"""Correlation scoring algorithms."""

from typing import Optional, Tuple
from datetime import timedelta
from sqlalchemy.orm import Session
import math

from app.models.alarm import Alarm
from app.core.constants import SEVERITY_SCORES, AlarmSeverity
from app.services.topology_service import TopologyService


class CorrelationScorer:
    """Calculates correlation scores between alarms."""

    def __init__(self, db: Session):
        """Initialize scorer."""
        self.db = db
        self.topology = TopologyService()

    def calculate_correlation_score(self, alarm1: Alarm, alarm2: Alarm) -> float:
        """
        Calculate correlation score between two alarms (0-1).

        Factors considered:
        1. Temporal proximity (0-0.25)
        2. Topological relationship (0-0.25)
        3. Device dependency (0-0.25)
        4. Severity correlation (0-0.15)
        5. Event type relationship (0-0.10)

        Total: 1.0 (normalized)
        """
        score = 0.0

        # 1. Temporal score (proximity in time)
        temporal_score = self._calculate_temporal_score(alarm1, alarm2)
        score += temporal_score * 0.25

        # 2. Topological score (network adjacency)
        topology_score = self._calculate_topology_score(alarm1, alarm2)
        score += topology_score * 0.25

        # 3. Dependency score (device relationships)
        dependency_score = self._calculate_dependency_score(alarm1, alarm2)
        score += dependency_score * 0.25

        # 4. Severity correlation
        severity_score = self._calculate_severity_score(alarm1, alarm2)
        score += severity_score * 0.15

        # 5. Event type relationship
        type_score = self._calculate_type_score(alarm1, alarm2)
        score += type_score * 0.10

        # Normalize to 0-1
        return min(1.0, max(0.0, score))

    def _calculate_temporal_score(self, alarm1: Alarm, alarm2: Alarm) -> float:
        """
        Score based on temporal proximity.

        Logic:
        - Same second: 1.0
        - Within 10 seconds: 0.8
        - Within 60 seconds: 0.5
        - Within 5 minutes: 0.2
        - Beyond 5 minutes: 0.0
        """
        time_diff = abs((alarm2.timestamp - alarm1.timestamp).total_seconds())

        if time_diff == 0:
            return 1.0
        elif time_diff <= 10:
            return 0.8
        elif time_diff <= 60:
            return 0.5
        elif time_diff <= 300:  # 5 minutes
            return 0.2
        else:
            return 0.0

    def _calculate_topology_score(self, alarm1: Alarm, alarm2: Alarm) -> float:
        """
        Score based on topological relationship.

        Logic:
        - Same device: 1.0
        - Adjacent devices (direct link): 0.8
        - Same subnet/region: 0.5
        - Different regions: 0.0
        """
        if alarm1.device_id == alarm2.device_id:
            return 1.0

        try:
            # Check if devices are adjacent (connected by link)
            device1_links = TopologyService.get_device_links(self.db, alarm1.device_id)
            device1_neighbors = set()

            for link in device1_links:
                # Get target device from link
                from app.models.device import Interface

                source_iface = self.db.query(Interface).filter(
                    Interface.id == link.source_interface_id
                ).first()
                target_iface = self.db.query(Interface).filter(
                    Interface.id == link.target_interface_id
                ).first()

                if source_iface and source_iface.device_id == alarm1.device_id:
                    if target_iface:
                        device1_neighbors.add(target_iface.device_id)
                elif target_iface and target_iface.device_id == alarm1.device_id:
                    if source_iface:
                        device1_neighbors.add(source_iface.device_id)

            if alarm2.device_id in device1_neighbors:
                return 0.8

            # Check same region (rough heuristic: similar device type or IP range)
            if self._in_same_region(alarm1.device_id, alarm2.device_id):
                return 0.5

            return 0.0

        except Exception:
            return 0.0

    def _calculate_dependency_score(self, alarm1: Alarm, alarm2: Alarm) -> float:
        """
        Score based on device dependencies.

        Logic:
        - One is upstream of other: 0.9
        - Both affected by same upstream: 0.7
        - Sibling devices: 0.4
        - Independent: 0.0
        """
        try:
            # Check if alarm2 device is downstream of alarm1
            blast_radius = TopologyService.get_blast_radius(self.db, alarm1.device_id)
            if alarm2.device_id in blast_radius:
                return 0.9

            # Check if alarm1 device is downstream of alarm2
            blast_radius = TopologyService.get_blast_radius(self.db, alarm2.device_id)
            if alarm1.device_id in blast_radius:
                return 0.9

            # Check if they have common upstream
            upstream1 = TopologyService.get_upstream_device(self.db, alarm1.device_id)
            upstream2 = TopologyService.get_upstream_device(self.db, alarm2.device_id)

            if upstream1 and upstream1 == upstream2:
                return 0.7

            # Sibling devices (same parent)
            if upstream1 and upstream1 == upstream2:
                return 0.4

            return 0.0

        except Exception:
            return 0.0

    def _calculate_severity_score(self, alarm1: Alarm, alarm2: Alarm) -> float:
        """
        Score based on severity correlation.

        Logic:
        - Both critical: 1.0
        - Both same severity: 0.8
        - Adjacent severity levels: 0.5
        - Different severity levels: 0.2
        """
        if alarm1.severity == alarm2.severity:
            if alarm1.severity == AlarmSeverity.CRITICAL:
                return 1.0
            return 0.8

        severity_order = [
            AlarmSeverity.CRITICAL,
            AlarmSeverity.MAJOR,
            AlarmSeverity.MINOR,
            AlarmSeverity.WARNING,
            AlarmSeverity.INFORMATIONAL,
            AlarmSeverity.DEBUG,
        ]

        try:
            idx1 = severity_order.index(alarm1.severity)
            idx2 = severity_order.index(alarm2.severity)
            distance = abs(idx1 - idx2)

            if distance == 1:
                return 0.5
            else:
                return 0.2
        except ValueError:
            return 0.2

    def _calculate_type_score(self, alarm1: Alarm, alarm2: Alarm) -> float:
        """
        Score based on event type relationship.

        Logic:
        - Same alarm type: 1.0
        - Related types (e.g., down + unreachable): 0.7
        - Unrelated types: 0.0
        """
        if alarm1.alarm_type == alarm2.alarm_type:
            return 1.0

        # Define related types
        related_pairs = [
            ("interface_down", "device_unreachable"),
            ("interface_down", "interface_recovery"),
            ("device_unreachable", "device_recovery"),
            ("interface_degraded", "high_latency"),
            ("interface_degraded", "packet_loss"),
        ]

        alarm_type_pair = (alarm1.alarm_type.value, alarm2.alarm_type.value)
        reverse_pair = (alarm2.alarm_type.value, alarm1.alarm_type.value)

        if alarm_type_pair in related_pairs or reverse_pair in related_pairs:
            return 0.7

        return 0.0

    def _in_same_region(self, device_id1: str, device_id2: str) -> bool:
        """Check if two devices are in the same region (heuristic)."""
        try:
            from app.models.device import Device

            device1 = self.db.query(Device).filter(Device.id == device_id1).first()
            device2 = self.db.query(Device).filter(Device.id == device_id2).first()

            if not device1 or not device2:
                return False

            # Simple heuristic: same device type layer
            return device1.device_type == device2.device_type

        except Exception:
            return False
