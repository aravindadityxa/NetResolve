"""Alarm management service."""

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
import uuid

from app.core.logging import logger
from app.core.constants import AlarmStatus, AlarmSeverity, SEVERITY_SCORES
from app.models.alarm import Alarm
from app.schemas.alarm import AlarmCreateSchema


class AlarmService:
    """Service for managing alarms."""

    @staticmethod
    def get_alarm(db: Session, alarm_id: str) -> Optional[Alarm]:
        """Get an alarm by ID."""
        return db.query(Alarm).filter(Alarm.id == alarm_id).first()

    @staticmethod
    def get_alarm_by_event_id(db: Session, event_id: str) -> Optional[Alarm]:
        """Get an alarm by event ID."""
        return db.query(Alarm).filter(Alarm.event_id == event_id).first()

    @staticmethod
    def list_alarms(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: Optional[AlarmStatus] = None,
        severity: Optional[AlarmSeverity] = None,
        device_id: Optional[str] = None,
    ) -> List[Alarm]:
        """List alarms with optional filters."""
        query = db.query(Alarm)

        if status:
            query = query.filter(Alarm.status == status)
        if severity:
            query = query.filter(Alarm.severity == severity)
        if device_id:
            query = query.filter(Alarm.device_id == device_id)

        return query.order_by(desc(Alarm.timestamp)).offset(skip).limit(limit).all()

    @staticmethod
    def get_recent_alarms(db: Session, seconds: int = 300) -> List[Alarm]:
        """Get alarms from the last N seconds."""
        since = datetime.utcnow() - timedelta(seconds=seconds)
        return (
            db.query(Alarm)
            .filter(Alarm.timestamp > since)
            .order_by(desc(Alarm.timestamp))
            .all()
        )

    @staticmethod
    def create_alarm(db: Session, alarm_data: AlarmCreateSchema) -> Alarm:
        """Create a new alarm."""
        alarm = Alarm(
            id=str(uuid.uuid4()),
            event_id=alarm_data.event_id,
            timestamp=alarm_data.timestamp,
            device_id=alarm_data.device_id,
            device_hostname=alarm_data.device_hostname,
            interface_id=alarm_data.interface_id,
            alarm_type=alarm_data.alarm_type,
            severity=alarm_data.severity,
            message=alarm_data.message,
            source=alarm_data.source,
            raw_data=alarm_data.raw_data,
            first_seen=alarm_data.timestamp,
            last_seen=alarm_data.timestamp,
        )
        db.add(alarm)
        db.commit()
        db.refresh(alarm)
        logger.info(
            f"Created alarm: {alarm.alarm_type} on {alarm.device_hostname} "
            f"({alarm.severity.value})"
        )
        return alarm

    @staticmethod
    def update_alarm_status(
        db: Session,
        alarm_id: str,
        status: AlarmStatus,
        correlation_id: Optional[str] = None,
    ) -> Optional[Alarm]:
        """Update alarm status."""
        alarm = db.query(Alarm).filter(Alarm.id == alarm_id).first()
        if alarm:
            alarm.status = status
            alarm.last_seen = datetime.utcnow()
            if correlation_id:
                alarm.correlation_id = correlation_id
            db.commit()
            db.refresh(alarm)
        return alarm

    @staticmethod
    def suppress_alarm(db: Session, alarm_id: str) -> Optional[Alarm]:
        """Mark an alarm as suppressed."""
        return AlarmService.update_alarm_status(db, alarm_id, AlarmStatus.SUPPRESSED)

    @staticmethod
    def get_open_alarms(db: Session) -> List[Alarm]:
        """Get all open alarms."""
        return db.query(Alarm).filter(Alarm.status == AlarmStatus.OPEN).all()

    @staticmethod
    def get_alarm_severity_distribution(db: Session) -> dict:
        """Get distribution of alarms by severity."""
        result = db.query(Alarm.severity).all()
        distribution = {}
        for severity_tuple in result:
            severity = severity_tuple[0]
            distribution[severity.value] = distribution.get(severity.value, 0) + 1
        return distribution

    @staticmethod
    def get_alarm_count_by_device(db: Session) -> dict:
        """Get alarm count for each device."""
        result = db.query(Alarm.device_hostname).all()
        counts = {}
        for hostname_tuple in result:
            hostname = hostname_tuple[0]
            counts[hostname] = counts.get(hostname, 0) + 1
        return counts

    @staticmethod
    def deduplicate_alarm(db: Session, device_id: str, alarm_type: str) -> Optional[Alarm]:
        """
        Find an existing open alarm of the same type on the same device
        within the last 5 minutes. Used to increment occurrence count
        instead of creating a duplicate.
        """
        from app.core.constants import ALARM_DEDUP_WINDOW_SECONDS

        since = datetime.utcnow() - timedelta(seconds=ALARM_DEDUP_WINDOW_SECONDS)
        existing = (
            db.query(Alarm)
            .filter(
                and_(
                    Alarm.device_id == device_id,
                    Alarm.alarm_type == alarm_type,
                    Alarm.status == AlarmStatus.OPEN,
                    Alarm.timestamp > since,
                )
            )
            .order_by(desc(Alarm.timestamp))
            .first()
        )

        if existing:
            existing.occurrence_count += 1
            existing.last_seen = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            logger.info(
                f"Deduplicated alarm: {alarm_type} on {device_id} "
                f"(count={existing.occurrence_count})"
            )

        return existing
