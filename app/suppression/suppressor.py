"""Alarm suppression engine - suppresses secondary alarms."""

from typing import List, Dict
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.logging import logger
from app.core.constants import AlarmStatus
from app.models.alarm import Alarm
from app.models.incident import IncidentAlarm
from app.services.alarm_service import AlarmService


class AlarmSuppressor:
    """Suppresses secondary alarms based on RCA results."""

    def __init__(self, db: Session):
        """Initialize suppressor."""
        self.db = db

    def suppress_secondary_alarms(
        self,
        root_cause_alarm_id: str,
        secondary_alarm_ids: List[str],
        reason: str = "Secondary alarm: downstream consequence of root cause",
    ) -> Dict:
        """
        Suppress secondary alarms.

        Args:
            root_cause_alarm_id: ID of the root cause alarm
            secondary_alarm_ids: List of alarm IDs to suppress
            reason: Suppression reason message

        Returns:
            Dict with suppression results
        """
        suppressed_count = 0
        failed_count = 0

        for alarm_id in secondary_alarm_ids:
            try:
                alarm = self.db.query(Alarm).filter(Alarm.id == alarm_id).first()
                if alarm:
                    alarm.status = AlarmStatus.SUPPRESSED
                    alarm.parent_alarm_id = root_cause_alarm_id
                    self.db.commit()
                    suppressed_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Error suppressing alarm {alarm_id}: {e}")
                failed_count += 1

        logger.info(
            f"Suppressed {suppressed_count} alarms "
            f"(reason: {reason})"
        )

        return {
            "suppressed_count": suppressed_count,
            "failed_count": failed_count,
            "reason": reason,
        }

    def unsuppress_alarms(self, alarm_ids: List[str]) -> int:
        """Unsuppress alarms."""
        count = 0
        for alarm_id in alarm_ids:
            try:
                alarm = self.db.query(Alarm).filter(Alarm.id == alarm_id).first()
                if alarm and alarm.status == AlarmStatus.SUPPRESSED:
                    alarm.status = AlarmStatus.OPEN
                    alarm.parent_alarm_id = None
                    self.db.commit()
                    count += 1
            except Exception as e:
                logger.error(f"Error unsuppressing alarm {alarm_id}: {e}")

        logger.info(f"Unsuppressed {count} alarms")
        return count

    def get_suppression_statistics(self) -> Dict:
        """Get suppression statistics."""
        total_alarms = self.db.query(Alarm).count()
        suppressed_alarms = self.db.query(Alarm).filter(
            Alarm.status == AlarmStatus.SUPPRESSED
        ).count()
        open_alarms = self.db.query(Alarm).filter(
            Alarm.status == AlarmStatus.OPEN
        ).count()

        return {
            "total_alarms": total_alarms,
            "suppressed_alarms": suppressed_alarms,
            "open_alarms": open_alarms,
            "suppression_ratio": suppressed_alarms / total_alarms if total_alarms > 0 else 0,
        }
