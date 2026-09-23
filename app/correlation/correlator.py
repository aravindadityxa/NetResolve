"""Alarm correlation engine - groups related alarms."""

from typing import List, Dict, Optional, Set, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import uuid

from app.core.logging import logger
from app.core.constants import (
    CORRELATION_SCORE_THRESHOLD,
    ALARM_DEDUP_WINDOW_SECONDS,
)
from app.models.alarm import Alarm
from app.services.alarm_service import AlarmService
from app.services.topology_service import TopologyService
from app.correlation.scorer import CorrelationScorer


class AlarmCorrelator:
    """Correlates related alarms into groups."""

    def __init__(self, db: Session):
        """Initialize correlator."""
        self.db = db
        self.scorer = CorrelationScorer(db)

    def correlate_alarms(self) -> List[Dict]:
        """
        Correlate recent alarms into groups.

        Returns:
            List of correlation groups with metadata
        """
        # Get recent uncorrelated alarms
        recent_alarms = AlarmService.get_recent_alarms(
            self.db,
            seconds=ALARM_DEDUP_WINDOW_SECONDS,
        )

        if not recent_alarms:
            logger.debug("No recent alarms to correlate")
            return []

        # Filter out already correlated alarms
        uncorrelated = [
            a for a in recent_alarms
            if a.correlation_id is None or a.status.value == "open"
        ]

        if not uncorrelated:
            logger.debug("All recent alarms already correlated")
            return []

        logger.info(f"Correlating {len(uncorrelated)} alarms")

        # Group alarms
        correlation_groups = self._group_alarms(uncorrelated)

        # Store correlation results
        results = []
        for group_id, alarms_in_group in correlation_groups.items():
            result = self._save_correlation_group(group_id, alarms_in_group)
            results.append(result)

        logger.info(f"Created {len(results)} correlation groups")
        return results

    def _group_alarms(self, alarms: List[Alarm]) -> Dict[str, List[Alarm]]:
        """
        Group alarms using multi-signal correlation.

        Algorithm:
        1. Sort alarms by timestamp (earliest first)
        2. For each alarm, try to correlate with existing groups
        3. If score > threshold, add to group
        4. Else, create new group
        """
        groups: Dict[str, List[Alarm]] = {}
        group_map: Dict[str, str] = {}  # alarm_id -> group_id

        # Sort by timestamp
        sorted_alarms = sorted(alarms, key=lambda a: a.timestamp)

        for alarm in sorted_alarms:
            best_group_id = None
            best_score = 0.0

            # Try to correlate with existing groups
            for group_id, group_alarms in groups.items():
                # Calculate correlation score with first alarm in group (representative)
                representative = group_alarms[0]
                score = self.scorer.calculate_correlation_score(alarm, representative)

                if score > best_score:
                    best_score = score
                    best_group_id = group_id

            # Decide whether to join group or create new one
            if best_score >= CORRELATION_SCORE_THRESHOLD and best_group_id:
                groups[best_group_id].append(alarm)
                group_map[alarm.id] = best_group_id
                logger.debug(
                    f"Alarm {alarm.id} correlated to group {best_group_id} "
                    f"(score: {best_score:.3f})"
                )
            else:
                # Create new group
                new_group_id = str(uuid.uuid4())
                groups[new_group_id] = [alarm]
                group_map[alarm.id] = new_group_id
                logger.debug(f"Alarm {alarm.id} created new correlation group")

        return groups

    def _save_correlation_group(
        self,
        group_id: str,
        alarms: List[Alarm],
    ) -> Dict:
        """Save correlation group to database."""
        try:
            # Assign correlation ID to all alarms in group
            for alarm in alarms:
                alarm.correlation_id = group_id
                self.db.commit()

            # Calculate group statistics
            stats = self._calculate_group_stats(alarms)

            logger.debug(
                f"Saved correlation group {group_id} "
                f"with {len(alarms)} alarms, score: {stats['avg_score']:.3f}"
            )

            return {
                "correlation_id": group_id,
                "alarm_count": len(alarms),
                "severity": alarms[0].severity.value if alarms else "unknown",
                "root_alarm_id": alarms[0].id if alarms else None,
                "average_score": stats["avg_score"],
                "score_distribution": stats["score_distribution"],
            }

        except Exception as e:
            logger.error(f"Error saving correlation group: {e}")
            return {}

    def _calculate_group_stats(self, alarms: List[Alarm]) -> Dict:
        """Calculate statistics for a correlation group."""
        if not alarms:
            return {"avg_score": 0.0, "score_distribution": {}}

        if len(alarms) == 1:
            return {
                "avg_score": 1.0,
                "score_distribution": {"perfect": 1},
            }

        # Calculate pairwise scores
        scores = []
        for i, alarm1 in enumerate(alarms):
            for alarm2 in alarms[i + 1:]:
                score = self.scorer.calculate_correlation_score(alarm1, alarm2)
                scores.append(score)

        avg_score = sum(scores) / len(scores) if scores else 0.0

        # Distribution buckets
        distribution = {
            "high": len([s for s in scores if s >= 0.8]),
            "medium": len([s for s in scores if 0.5 <= s < 0.8]),
            "low": len([s for s in scores if 0.2 <= s < 0.5]),
        }

        return {
            "avg_score": avg_score,
            "score_distribution": distribution,
        }

    def get_correlation_group(self, correlation_id: str) -> Optional[Dict]:
        """Get a correlation group by ID."""
        alarms = (
            self.db.query(Alarm)
            .filter(Alarm.correlation_id == correlation_id)
            .all()
        )

        if not alarms:
            return None

        return {
            "correlation_id": correlation_id,
            "alarms": [
                {
                    "id": a.id,
                    "device_id": a.device_id,
                    "device_hostname": a.device_hostname,
                    "alarm_type": a.alarm_type.value,
                    "severity": a.severity.value,
                    "timestamp": a.timestamp.isoformat(),
                    "message": a.message,
                }
                for a in alarms
            ],
            "count": len(alarms),
            "first_event": min(a.timestamp for a in alarms).isoformat(),
            "last_event": max(a.timestamp for a in alarms).isoformat(),
        }

    def get_correlation_groups(self, limit: int = 100) -> List[Dict]:
        """Get recent correlation groups."""
        # Get unique correlation IDs
        query = (
            self.db.query(Alarm.correlation_id)
            .distinct()
            .filter(Alarm.correlation_id.isnot(None))
            .order_by(Alarm.created_at.desc())
            .limit(limit)
            .all()
        )

        groups = []
        for (correlation_id,) in query:
            group = self.get_correlation_group(correlation_id)
            if group:
                groups.append(group)

        return groups

    def update_correlation_metadata(
        self,
        correlation_id: str,
        root_cause_alarm_id: Optional[str] = None,
        confidence: Optional[float] = None,
        reasoning: Optional[str] = None,
    ) -> bool:
        """Update metadata for a correlation group."""
        try:
            alarms = (
                self.db.query(Alarm)
                .filter(Alarm.correlation_id == correlation_id)
                .all()
            )

            for alarm in alarms:
                if root_cause_alarm_id and alarm.id == root_cause_alarm_id:
                    alarm.probable_root_cause = True
                if confidence is not None:
                    alarm.confidence = confidence

            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating correlation metadata: {e}")
            return False
