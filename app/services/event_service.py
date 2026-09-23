"""Network event management service."""

from typing import List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
import uuid

from app.core.logging import logger
from app.models.event import NetworkEvent
from app.schemas.event import NetworkEventSchema


class EventService:
    """Service for managing raw network events."""

    @staticmethod
    def get_event(db: Session, event_id: str) -> NetworkEvent:
        """Get an event by ID."""
        return db.query(NetworkEvent).filter(NetworkEvent.id == event_id).first()

    @staticmethod
    def get_event_by_event_id(db: Session, event_id: str) -> NetworkEvent:
        """Get an event by event_id (unique source ID)."""
        return db.query(NetworkEvent).filter(NetworkEvent.event_id == event_id).first()

    @staticmethod
    def list_events(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        device_id: str = None,
        source: str = None,
    ) -> List[NetworkEvent]:
        """List events with optional filters."""
        query = db.query(NetworkEvent)

        if device_id:
            query = query.filter(NetworkEvent.device_id == device_id)
        if source:
            query = query.filter(NetworkEvent.source == source)

        return query.order_by(desc(NetworkEvent.timestamp)).offset(skip).limit(limit).all()

    @staticmethod
    def get_recent_events(db: Session, seconds: int = 300) -> List[NetworkEvent]:
        """Get events from the last N seconds."""
        since = datetime.utcnow() - timedelta(seconds=seconds)
        return (
            db.query(NetworkEvent)
            .filter(NetworkEvent.timestamp > since)
            .order_by(desc(NetworkEvent.timestamp))
            .all()
        )

    @staticmethod
    def create_event(db: Session, event_data: NetworkEventSchema) -> NetworkEvent:
        """Create a new network event."""
        event = NetworkEvent(
            id=str(uuid.uuid4()),
            event_id=event_data.event_id,
            timestamp=event_data.timestamp,
            source=event_data.source,
            device_id=event_data.device_id,
            device_hostname=event_data.device_hostname,
            event_type=event_data.event_type,
            interface_id=event_data.interface_id,
            severity=event_data.severity,
            message=event_data.message,
            raw_data=event_data.raw_data,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        logger.info(
            f"Created event: {event.event_type} on {event.device_hostname} "
            f"from {event.source}"
        )
        return event

    @staticmethod
    def get_event_count(db: Session) -> int:
        """Get total event count."""
        return db.query(NetworkEvent).count()

    @staticmethod
    def get_event_count_by_source(db: Session) -> dict:
        """Get event count by source."""
        result = db.query(NetworkEvent.source).all()
        counts = {}
        for source_tuple in result:
            source = source_tuple[0]
            counts[source] = counts.get(source, 0) + 1
        return counts

    @staticmethod
    def get_event_count_by_type(db: Session) -> dict:
        """Get event count by type."""
        result = db.query(NetworkEvent.event_type).all()
        counts = {}
        for event_type_tuple in result:
            event_type = event_type_tuple[0]
            counts[event_type] = counts.get(event_type, 0) + 1
        return counts
