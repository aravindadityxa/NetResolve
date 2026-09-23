"""Incident management service."""

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
import uuid

from app.core.logging import logger
from app.core.constants import IncidentState
from app.models.incident import Incident, IncidentAlarm, TimelineEvent
from app.models.alarm import Alarm


class IncidentService:
    """Service for managing incidents."""

    @staticmethod
    def get_incident(db: Session, incident_id: str) -> Optional[Incident]:
        """Get an incident by ID."""
        return db.query(Incident).filter(Incident.id == incident_id).first()

    @staticmethod
    def list_incidents(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        state: Optional[IncidentState] = None,
        resolved_only: bool = False,
    ) -> List[Incident]:
        """List incidents with optional filters."""
        query = db.query(Incident)

        if state:
            query = query.filter(Incident.state == state)
        if resolved_only:
            query = query.filter(Incident.state == IncidentState.RESOLVED)

        return query.order_by(desc(Incident.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    def get_active_incidents(db: Session) -> List[Incident]:
        """Get all active incidents."""
        return (
            db.query(Incident)
            .filter(
                Incident.state.in_(
                    [
                        IncidentState.OPEN,
                        IncidentState.CORRELATED,
                        IncidentState.ROOT_CAUSE_IDENTIFIED,
                        IncidentState.ACTIVE,
                        IncidentState.RECOVERING,
                    ]
                )
            )
            .order_by(desc(Incident.created_at))
            .all()
        )

    @staticmethod
    def create_incident(
        db: Session,
        severity: str,
        root_cause_device_id: Optional[str] = None,
        probable_root_cause: Optional[str] = None,
    ) -> Incident:
        """Create a new incident."""
        incident = Incident(
            id=str(uuid.uuid4()),
            severity=severity,
            root_cause_device_id=root_cause_device_id,
            probable_root_cause=probable_root_cause,
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)
        logger.info(f"Created incident: {incident.id} ({severity})")
        return incident

    @staticmethod
    def update_incident_state(
        db: Session, incident_id: str, state: IncidentState
    ) -> Optional[Incident]:
        """Update incident state."""
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if incident:
            incident.state = state
            incident.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(incident)
            logger.info(f"Updated incident {incident_id} to state: {state}")
        return incident

    @staticmethod
    def update_incident_rca(
        db: Session,
        incident_id: str,
        root_cause_device_id: Optional[str] = None,
        root_cause_interface_id: Optional[str] = None,
        probable_root_cause: Optional[str] = None,
        rca_confidence: Optional[float] = None,
        rca_reasoning: Optional[str] = None,
    ) -> Optional[Incident]:
        """Update incident with RCA results."""
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if incident:
            if root_cause_device_id:
                incident.root_cause_device_id = root_cause_device_id
            if root_cause_interface_id:
                incident.root_cause_interface_id = root_cause_interface_id
            if probable_root_cause:
                incident.probable_root_cause = probable_root_cause
            if rca_confidence is not None:
                incident.rca_confidence = rca_confidence
            if rca_reasoning:
                incident.rca_reasoning = rca_reasoning
            incident.updated_at = datetime.utcnow()
            incident.state = IncidentState.ROOT_CAUSE_IDENTIFIED
            db.commit()
            db.refresh(incident)
        return incident

    @staticmethod
    def resolve_incident(db: Session, incident_id: str) -> Optional[Incident]:
        """Mark incident as resolved."""
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if incident:
            incident.state = IncidentState.RESOLVED
            incident.resolved_at = datetime.utcnow()
            incident.updated_at = datetime.utcnow()

            # Calculate MTTR
            if incident.created_at:
                incident.mttr = (incident.resolved_at - incident.created_at).total_seconds()

            db.commit()
            db.refresh(incident)
            logger.info(f"Resolved incident {incident_id}")
        return incident

    @staticmethod
    def add_alarm_to_incident(
        db: Session,
        incident_id: str,
        alarm_id: str,
        is_suppressed: bool = False,
        suppression_reason: Optional[str] = None,
    ) -> IncidentAlarm:
        """Add an alarm to an incident."""
        incident_alarm = IncidentAlarm(
            id=str(uuid.uuid4()),
            incident_id=incident_id,
            alarm_id=alarm_id,
            is_suppressed=is_suppressed,
            suppression_reason=suppression_reason,
        )
        db.add(incident_alarm)
        db.commit()
        db.refresh(incident_alarm)

        # Update incident suppression count
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if incident and is_suppressed:
            incident.suppression_count += 1
            db.commit()

        return incident_alarm

    @staticmethod
    def add_timeline_event(
        db: Session,
        incident_id: str,
        event_type: str,
        message: str,
        device_id: Optional[str] = None,
        device_hostname: Optional[str] = None,
        alarm_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> TimelineEvent:
        """Add an event to incident timeline."""
        if not timestamp:
            timestamp = datetime.utcnow()

        event = TimelineEvent(
            id=str(uuid.uuid4()),
            incident_id=incident_id,
            timestamp=timestamp,
            device_id=device_id,
            device_hostname=device_hostname,
            event_type=event_type,
            message=message,
            alarm_id=alarm_id,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def get_incident_alarms(db: Session, incident_id: str) -> List[IncidentAlarm]:
        """Get all alarms for an incident."""
        return (
            db.query(IncidentAlarm)
            .filter(IncidentAlarm.incident_id == incident_id)
            .all()
        )

    @staticmethod
    def get_incident_timeline(db: Session, incident_id: str) -> List[TimelineEvent]:
        """Get timeline events for an incident."""
        return (
            db.query(TimelineEvent)
            .filter(TimelineEvent.incident_id == incident_id)
            .order_by(TimelineEvent.timestamp)
            .all()
        )

    @staticmethod
    def get_incident_count(db: Session) -> int:
        """Get total incident count."""
        return db.query(Incident).count()

    @staticmethod
    def get_active_incident_count(db: Session) -> int:
        """Get count of active incidents."""
        return len(IncidentService.get_active_incidents(db))
