"""RCA reasoning and explanation generation."""

from typing import List, Dict
from sqlalchemy.orm import Session

from app.models.alarm import Alarm
from app.core.logging import logger


class RCAReasoner:
    """Generates human-readable reasoning for RCA results."""

    def __init__(self, db: Session):
        """Initialize reasoner."""
        self.db = db

    def generate_reasoning(
        self,
        root_cause_alarm: Alarm,
        all_alarms: List[Alarm],
        affected_devices: List[str],
        rca_score: Dict,
    ) -> str:
        """
        Generate detailed reasoning for RCA result.

        Returns:
            Human-readable explanation of why this alarm is the root cause
        """
        lines = []

        # Header
        lines.append(f"Root Cause Analysis for {len(all_alarms)} correlated alarms:")
        lines.append("")

        # Root cause identification
        lines.append(
            f"Root Cause: {root_cause_alarm.device_hostname} - "
            f"{root_cause_alarm.alarm_type.value.upper()}"
        )
        if root_cause_alarm.interface_id:
            lines.append(f"  Interface: {root_cause_alarm.interface_id}")
        lines.append(f"  Time: {root_cause_alarm.timestamp.isoformat()}")
        lines.append(f"  Message: {root_cause_alarm.message}")
        lines.append("")

        # Evidence
        lines.append("Evidence:")

        # Temporal evidence
        if rca_score["factors"].get("temporal", 0) > 0.7:
            lines.append(
                f"  ✓ First event: This alarm appeared first in the sequence, "
                f"suggesting it is the initial failure"
            )
        elif rca_score["factors"].get("temporal", 0) > 0.4:
            lines.append(
                f"  ~ Early event: This alarm appeared early but not first"
            )

        # Topology evidence
        if rca_score["factors"].get("topology", 0) > 0.7:
            lines.append(
                f"  ✓ Upstream location: Device is located upstream of "
                f"{len(affected_devices)} affected devices in the network hierarchy"
            )
        elif rca_score["factors"].get("topology", 0) > 0.4:
            lines.append(
                f"  ~ Partial upstream: Some affected devices are downstream of this device"
            )

        # Cascade evidence
        if rca_score["factors"].get("cascade", 0) > 0.7:
            cascade_count = len([a for a in all_alarms if a.id != root_cause_alarm.id])
            if cascade_count > 0:
                lines.append(
                    f"  ✓ Cascading pattern: {cascade_count} secondary alarms "
                    f"appeared after this primary failure"
                )

        # Severity evidence
        if rca_score["factors"].get("severity", 0) > 0.6:
            lines.append(
                f"  ✓ High severity: Alarm severity ({root_cause_alarm.severity.value}) "
                f"is consistent with a root cause event"
            )

        lines.append("")

        # Impact summary
        lines.append(f"Impact Summary:")
        lines.append(f"  Directly affected: {len(affected_devices)} device(s)")
        if affected_devices:
            # Show first few affected devices
            shown_devices = affected_devices[:3]
            lines.append(f"  Affected devices: {', '.join(shown_devices)}")
            if len(affected_devices) > 3:
                lines.append(f"    ... and {len(affected_devices) - 3} more")

        lines.append("")

        # Confidence and caveats
        confidence = rca_score.get("confidence", 0)
        lines.append(f"Confidence: {confidence:.1%}")

        if confidence < 0.70:
            lines.append(
                "  Note: Confidence is below optimal. Multiple root causes may be possible."
            )
        elif confidence >= 0.90:
            lines.append(
                "  Note: High confidence. This is the most likely root cause."
            )

        return "\n".join(lines)

    def generate_brief_reasoning(
        self,
        root_cause_alarm: Alarm,
        all_alarms: List[Alarm],
        affected_devices: List[str],
        confidence: float,
    ) -> str:
        """
        Generate brief one-line reasoning.

        Used for dashboard tooltips and summaries.
        """
        device_count = len([a for a in all_alarms if a.id != root_cause_alarm.id])

        if device_count == 0:
            return f"Isolated failure on {root_cause_alarm.device_hostname}"

        if len(affected_devices) == 1:
            return f"Primary failure on {root_cause_alarm.device_hostname} affecting 1 device"

        return (
            f"Primary failure on {root_cause_alarm.device_hostname} "
            f"affecting {len(affected_devices)} device(s)"
        )

    def generate_remediation_suggestions(
        self,
        root_cause_alarm: Alarm,
    ) -> List[str]:
        """
        Generate remediation suggestions based on root cause.

        Returns:
            List of actionable suggestions
        """
        suggestions = []

        alarm_type = root_cause_alarm.alarm_type.value

        if alarm_type == "interface_down":
            suggestions.extend([
                f"Check physical connection to {root_cause_alarm.interface_id}",
                f"Verify cable and port status on {root_cause_alarm.device_hostname}",
                f"Check for port errors: show interface {root_cause_alarm.interface_id}",
                "If necessary, perform interface shutdown/no-shutdown cycle",
            ])

        elif alarm_type == "device_unreachable":
            suggestions.extend([
                f"Verify management connectivity to {root_cause_alarm.device_hostname}",
                "Check device power and boot status",
                f"Attempt SSH/telnet to {root_cause_alarm.device_hostname}",
                "Check routing to management network",
                "Review recent device logs for crash information",
            ])

        elif alarm_type == "high_latency":
            suggestions.extend([
                f"Check {root_cause_alarm.interface_id} utilization and errors",
                "Verify QoS policies are working correctly",
                "Check for congestion on upstream links",
                "Verify routing convergence (check BGP/OSPF neighbors)",
            ])

        elif alarm_type == "packet_loss":
            suggestions.extend([
                f"Check {root_cause_alarm.interface_id} for errors or CRC failures",
                "Verify physical layer health (optics, cables)",
                "Check for buffer drops or queue overruns",
                "Verify MTU settings on all hops",
            ])

        elif alarm_type == "link_flapping":
            suggestions.extend([
                f"Check {root_cause_alarm.interface_id} for hardware issues",
                "Verify cable quality and connections",
                "Check link partner for stability",
                "Disable auto-negotiation if applicable",
                "Monitor logs for SFP/optics issues",
            ])

        else:
            suggestions.append(
                f"Investigate {alarm_type} on {root_cause_alarm.device_hostname}"
            )

        return suggestions
