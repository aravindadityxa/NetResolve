"""Event normalization service."""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from app.core.logging import logger
from app.core.constants import AlarmType, AlarmSeverity
from app.schemas.alarm import AlarmCreateSchema


class EventNormalizer:
    """Normalizes raw events into standardized alarm format."""

    # Mapping from event types to alarm types
    EVENT_TO_ALARM_TYPE = {
        "interface_down": AlarmType.INTERFACE_DOWN,
        "interface_recovery": AlarmType.INTERFACE_RECOVERY,
        "device_unreachable": AlarmType.DEVICE_UNREACHABLE,
        "device_recovery": AlarmType.DEVICE_RECOVERY,
        "high_latency": AlarmType.HIGH_LATENCY,
        "packet_loss": AlarmType.PACKET_LOSS,
        "link_flapping": AlarmType.LINK_FLAPPING,
        "link_down": AlarmType.INTERFACE_DOWN,
        "link_up": AlarmType.INTERFACE_RECOVERY,
        "dependency_failure": AlarmType.DEPENDENCY_FAILURE,
    }

    # Mapping from severity strings to alarm severity
    SEVERITY_MAP = {
        "critical": AlarmSeverity.CRITICAL,
        "major": AlarmSeverity.MAJOR,
        "minor": AlarmSeverity.MINOR,
        "warning": AlarmSeverity.WARNING,
        "informational": AlarmSeverity.INFORMATIONAL,
        "debug": AlarmSeverity.DEBUG,
    }

    @staticmethod
    def normalize(event: Dict[str, Any]) -> Optional[AlarmCreateSchema]:
        """
        Normalize a raw event into an alarm schema.

        Args:
            event: Raw event dictionary

        Returns:
            AlarmCreateSchema if normalization succeeds, None otherwise
        """
        try:
            # Extract and validate required fields
            event_id = event.get("event_id")
            if not event_id:
                logger.warning("Event missing event_id")
                return None

            timestamp_str = event.get("timestamp")
            if isinstance(timestamp_str, str):
                timestamp = datetime.fromisoformat(timestamp_str)
            else:
                timestamp = timestamp_str or datetime.utcnow()

            device_id = event.get("device_id")
            device_hostname = event.get("device_hostname")
            event_type = event.get("event_type", "").lower()
            severity_str = event.get("severity", "informational").lower()
            message = event.get("message", "")

            if not all([device_id, device_hostname, event_type]):
                logger.warning(
                    f"Event {event_id} missing required fields: "
                    f"device_id={device_id}, device_hostname={device_hostname}, "
                    f"event_type={event_type}"
                )
                return None

            # Map event type to alarm type
            alarm_type = EventNormalizer.EVENT_TO_ALARM_TYPE.get(
                event_type,
                AlarmType.INTERFACE_DOWN,  # Default
            )

            # Map severity
            severity = EventNormalizer.SEVERITY_MAP.get(
                severity_str,
                AlarmSeverity.WARNING,  # Default
            )

            # Create correlation ID (events are grouped by correlation_id later)
            correlation_id = str(uuid.uuid4())

            # Create alarm schema
            alarm = AlarmCreateSchema(
                event_id=event_id,
                timestamp=timestamp,
                device_id=device_id,
                device_hostname=device_hostname,
                interface_id=event.get("interface_id"),
                alarm_type=alarm_type,
                severity=severity,
                message=message,
                source=event.get("source", "unknown"),
                raw_data=event,
            )

            logger.debug(f"Normalized event {event_id} to alarm: {alarm_type.value}")
            return alarm

        except Exception as e:
            logger.error(f"Error normalizing event: {e}")
            return None

    @staticmethod
    def batch_normalize(events: list) -> list:
        """
        Normalize a batch of events.

        Args:
            events: List of raw events

        Returns:
            List of normalized alarms
        """
        normalized = []
        for event in events:
            alarm = EventNormalizer.normalize(event)
            if alarm:
                normalized.append(alarm)

        logger.debug(f"Normalized {len(normalized)}/{len(events)} events")
        return normalized

    @staticmethod
    def get_correlation_hints(event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract hints for correlation from an event.

        Args:
            event: Event dictionary

        Returns:
            Dictionary with correlation hints
        """
        return {
            "device_id": event.get("device_id"),
            "device_hostname": event.get("device_hostname"),
            "event_type": event.get("event_type"),
            "interface_id": event.get("interface_id"),
            "severity": event.get("severity"),
            "timestamp": event.get("timestamp"),
            "source": event.get("source"),
        }
