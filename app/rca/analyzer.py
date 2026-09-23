"""Root Cause Analysis engine."""

from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import math

from app.core.logging import logger
from app.core.constants import RCA_CONFIDENCE_THRESHOLD
from app.models.alarm import Alarm
from app.services.alarm_service import AlarmService
from app.services.topology_service import TopologyService
from app.rca.scorer import RCAScorer
from app.rca.reasoner import RCAReasoner


class RCAAnalyzer:
    """Performs root cause analysis on correlated alarm groups."""

    def __init__(self, db: Session):
        """Initialize RCA analyzer."""
        self.db = db
        self.scorer = RCAScorer(db)
        self.reasoner = RCAReasoner(db)

    def analyze_correlation_group(self, correlation_id: str) -> Dict:
        """
        Perform RCA on a correlated alarm group.

        Returns:
            Dict with RCA results including:
            - root_cause_alarm_id
            - confidence
            - affected_devices
            - blast_radius
            - reasoning
        """
        # Get all alarms in group
        alarms = (
            self.db.query(Alarm)
            .filter(Alarm.correlation_id == correlation_id)
            .order_by(Alarm.timestamp.asc())
            .all()
        )

        if not alarms:
            logger.warning(f"No alarms found for correlation group {correlation_id}")
            return self._empty_rca_result()

        logger.info(f"Analyzing RCA for correlation group {correlation_id} ({len(alarms)} alarms)")

        # 1. Identify candidate root causes
        candidates = self._identify_root_cause_candidates(alarms)

        if not candidates:
            logger.warning("No root cause candidates identified")
            return self._empty_rca_result()

        # 2. Score each candidate
        scored_candidates = [
            (alarm, self.scorer.calculate_rca_score(alarm, alarms))
            for alarm in candidates
        ]

        # 3. Select best candidate
        best_candidate = max(scored_candidates, key=lambda x: x[1]["confidence"])
        root_cause_alarm, rca_score = best_candidate

        # 4. Calculate affected devices and blast radius
        affected_devices, blast_radius = self._calculate_impact(
            root_cause_alarm,
            alarms,
        )

        # 5. Generate reasoning
        reasoning = self.reasoner.generate_reasoning(
            root_cause_alarm,
            alarms,
            affected_devices,
            rca_score,
        )

        result = {
            "correlation_id": correlation_id,
            "root_cause_alarm_id": root_cause_alarm.id,
            "root_cause_device_id": root_cause_alarm.device_id,
            "root_cause_device_hostname": root_cause_alarm.device_hostname,
            "root_cause_interface_id": root_cause_alarm.interface_id,
            "root_cause_type": root_cause_alarm.alarm_type.value,
            "confidence": rca_score["confidence"],
            "confidence_factors": rca_score["factors"],
            "affected_devices": affected_devices,
            "blast_radius": len(affected_devices),
            "reasoning": reasoning,
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(
            f"RCA analysis complete: root_cause={root_cause_alarm.device_hostname} "
            f"({root_cause_alarm.alarm_type.value}), "
            f"confidence={rca_score['confidence']:.2%}, "
            f"affected_devices={len(affected_devices)}"
        )

        return result

    def _identify_root_cause_candidates(self, alarms: List[Alarm]) -> List[Alarm]:
        """
        Identify potential root cause alarms.

        Heuristics:
        1. Earliest alarm (first failure)
        2. Highest severity alarms
        3. Device unreachable alarms (primary failures)
        4. Interface down alarms (primary failures)
        """
        candidates = []

        # 1. Earliest alarm is likely root cause
        if alarms:
            earliest = min(alarms, key=lambda a: a.timestamp)
            candidates.append(earliest)

        # 2. Highest severity alarms
        max_severity_alarms = [
            a for a in alarms
            if a.severity == max(a.severity for a in alarms)
        ]
        candidates.extend(max_severity_alarms)

        # 3. Primary failure types (not secondary symptoms)
        primary_types = ["device_unreachable", "interface_down"]
        primary_alarms = [
            a for a in alarms
            if a.alarm_type.value in primary_types
        ]
        candidates.extend(primary_alarms)

        # Deduplicate and return
        return list(set(candidates))

    def _calculate_impact(
        self,
        root_cause_alarm: Alarm,
        all_alarms: List[Alarm],
    ) -> tuple[List[str], int]:
        """Calculate affected devices and blast radius."""
        try:
            # Get blast radius from topology
            blast_radius_devices = TopologyService.get_blast_radius(
                self.db,
                root_cause_alarm.device_id,
            )

            # Get all unique devices from alarms
            all_affected_devices = set()
            for alarm in all_alarms:
                all_affected_devices.add(alarm.device_id)

            # Filter to only downstream devices for this root cause
            affected_devices = [
                d for d in all_affected_devices
                if d in blast_radius_devices or d == root_cause_alarm.device_id
            ]

            return affected_devices, len(affected_devices)

        except Exception as e:
            logger.error(f"Error calculating impact: {e}")
            root_device = {root_cause_alarm.device_id}
            return list(root_device), 1

    def _empty_rca_result(self) -> Dict:
        """Return empty RCA result."""
        return {
            "correlation_id": None,
            "root_cause_alarm_id": None,
            "confidence": 0.0,
            "affected_devices": [],
            "blast_radius": 0,
            "reasoning": "Unable to determine root cause",
        }

    def analyze_recent_groups(self, limit: int = 10) -> List[Dict]:
        """Analyze recent correlation groups."""
        # Get recent correlation groups
        query = (
            self.db.query(Alarm.correlation_id)
            .distinct()
            .filter(Alarm.correlation_id.isnot(None))
            .filter(Alarm.probable_root_cause.is_(None))  # Not yet analyzed
            .order_by(Alarm.created_at.desc())
            .limit(limit)
            .all()
        )

        results = []
        for (correlation_id,) in query:
            rca_result = self.analyze_correlation_group(correlation_id)
            if rca_result.get("root_cause_alarm_id"):
                results.append(rca_result)

        return results
