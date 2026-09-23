"""RCA scoring calculations."""

from typing import Dict, List
from datetime import timedelta
from sqlalchemy.orm import Session
import math

from app.models.alarm import Alarm
from app.core.constants import SEVERITY_SCORES
from app.services.topology_service import TopologyService


class RCAScorer:
    """Calculates RCA scores for determining root cause."""

    def __init__(self, db: Session):
        """Initialize RCA scorer."""
        self.db = db

    def calculate_rca_score(
        self,
        candidate_alarm: Alarm,
        all_alarms: List[Alarm],
    ) -> Dict:
        """
        Calculate RCA score for a candidate root cause.

        Factors (each 0-1, normalized):
        1. Temporal factor (0.30): Is this the earliest alarm?
        2. Topology factor (0.25): Are affected alarms downstream?
        3. Cascade factor (0.25): Do secondary alarms follow in time?
        4. Severity factor (0.20): Is severity appropriate for root cause?

        Returns dict with confidence and factor breakdown.
        """
        factors = {}

        # 1. Temporal factor: earliest alarm has high score
        temporal_factor = self._calculate_temporal_factor(candidate_alarm, all_alarms)
        factors["temporal"] = temporal_factor

        # 2. Topology factor: affected devices should be downstream
        topology_factor = self._calculate_topology_factor(candidate_alarm, all_alarms)
        factors["topology"] = topology_factor

        # 3. Cascade factor: downstream alarms should follow in time
        cascade_factor = self._calculate_cascade_factor(candidate_alarm, all_alarms)
        factors["cascade"] = cascade_factor

        # 4. Severity factor: root cause should be high severity
        severity_factor = self._calculate_severity_factor(candidate_alarm, all_alarms)
        factors["severity"] = severity_factor

        # Calculate weighted confidence
        confidence = (
            temporal_factor * 0.30
            + topology_factor * 0.25
            + cascade_factor * 0.25
            + severity_factor * 0.20
        )

        return {
            "confidence": min(1.0, max(0.0, confidence)),
            "factors": factors,
        }

    def _calculate_temporal_factor(
        self,
        candidate_alarm: Alarm,
        all_alarms: List[Alarm],
    ) -> float:
        """
        Temporal factor: Is this the earliest alarm?

        Logic:
        - Is earliest: 1.0
        - Within 5 seconds of earliest: 0.8
        - Within 30 seconds of earliest: 0.5
        - Beyond 30 seconds: 0.2
        """
        if not all_alarms:
            return 0.5

        earliest_time = min(a.timestamp for a in all_alarms)
        time_diff = (candidate_alarm.timestamp - earliest_time).total_seconds()

        if time_diff == 0:
            return 1.0
        elif time_diff <= 5:
            return 0.8
        elif time_diff <= 30:
            return 0.5
        else:
            return 0.2

    def _calculate_topology_factor(
        self,
        candidate_alarm: Alarm,
        all_alarms: List[Alarm],
    ) -> float:
        """
        Topology factor: Are affected alarms downstream?

        Logic:
        - All other alarms are downstream: 1.0
        - 80%+ are downstream: 0.8
        - 50%+ are downstream: 0.6
        - 25%+ are downstream: 0.3
        - None downstream: 0.0
        """
        try:
            # Get blast radius from candidate device
            blast_radius = TopologyService.get_blast_radius(
                self.db,
                candidate_alarm.device_id,
            )

            # Count how many alarm devices are downstream
            affected_devices = [a.device_id for a in all_alarms if a.id != candidate_alarm.id]
            downstream_count = sum(
                1 for device_id in affected_devices
                if device_id in blast_radius
            )

            if not affected_devices:
                return 1.0  # Only one device, so it's the root

            downstream_ratio = downstream_count / len(affected_devices)

            if downstream_ratio >= 0.99:
                return 1.0
            elif downstream_ratio >= 0.80:
                return 0.8
            elif downstream_ratio >= 0.50:
                return 0.6
            elif downstream_ratio >= 0.25:
                return 0.3
            else:
                return 0.0

        except Exception:
            return 0.5

    def _calculate_cascade_factor(
        self,
        candidate_alarm: Alarm,
        all_alarms: List[Alarm],
    ) -> float:
        """
        Cascade factor: Do secondary alarms follow in time?

        Logic:
        - Secondary alarms appear 2-60s after root: 1.0
        - Secondary alarms appear 1-120s after root: 0.8
        - Secondary alarms appear >120s after root: 0.3
        - No secondary alarms: 0.5
        """
        other_alarms = [a for a in all_alarms if a.id != candidate_alarm.id]

        if not other_alarms:
            return 0.5  # Single alarm, neutral score

        # Check timing of secondary alarms relative to candidate
        secondary_times = [
            (a.timestamp - candidate_alarm.timestamp).total_seconds()
            for a in other_alarms
        ]

        # Secondary alarms should appear AFTER root cause
        appropriate_cascades = sum(
            1 for t in secondary_times
            if 0 < t < 120  # Cascades within 0-120 seconds
        )

        bad_cascades = sum(
            1 for t in secondary_times
            if t < 0  # Alarms before root cause (unlikely)
        )

        if bad_cascades > 0:
            # Alarms appearing before this one suggest it's not the root
            return 0.1

        ratio = appropriate_cascades / len(secondary_times) if secondary_times else 0

        if ratio >= 0.80:
            return 1.0
        elif ratio >= 0.50:
            return 0.8
        elif ratio >= 0.20:
            return 0.5
        else:
            return 0.2

    def _calculate_severity_factor(
        self,
        candidate_alarm: Alarm,
        all_alarms: List[Alarm],
    ) -> float:
        """
        Severity factor: Is severity appropriate for root cause?

        Logic:
        - Root cause should be high severity (CRITICAL or MAJOR)
        - Secondary alarms can be any severity
        """
        severity_value = SEVERITY_SCORES.get(candidate_alarm.severity, 50)

        if severity_value >= 80:  # CRITICAL or MAJOR
            return 1.0
        elif severity_value >= 60:  # MINOR
            return 0.7
        elif severity_value >= 40:  # WARNING
            return 0.5
        else:
            return 0.3
