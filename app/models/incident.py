"""Database models for incidents."""

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Enum,
    Float,
    Integer,
    Text,
    JSON,
    Table,
    Boolean,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base
from app.core.constants import IncidentState


class Incident(Base):
    """Incident model."""

    __tablename__ = "incidents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    state = Column(Enum(IncidentState), default=IncidentState.OPEN, index=True)
    severity = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime)
    root_cause_device_id = Column(String(36), ForeignKey("devices.id"))
    root_cause_interface_id = Column(String(36))
    root_cause_alarm_id = Column(String(36), ForeignKey("alarms.id"))
    probable_root_cause = Column(Text)
    rca_confidence = Column(Float)  # 0-1
    rca_reasoning = Column(Text)
    blast_radius = Column(Integer, default=0)
    suppression_count = Column(Integer, default=0)
    mttd = Column(Float)  # Mean time to detect
    mtti = Column(Float)  # Mean time to identify root cause
    mttr = Column(Float)  # Mean time to resolve
    extra_metadata = Column(JSON)

    # Relationships
    root_cause_device = relationship("Device")
    root_cause_alarm = relationship("Alarm")
    incident_alarms = relationship("IncidentAlarm", back_populates="incident", cascade="all, delete-orphan")
    timeline_events = relationship("TimelineEvent", back_populates="incident", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Incident {self.id} ({self.state})>"


class IncidentAlarm(Base):
    """Association between incidents and alarms."""

    __tablename__ = "incident_alarms"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), ForeignKey("incidents.id"), nullable=False, index=True)
    alarm_id = Column(String(36), ForeignKey("alarms.id"), nullable=False, index=True)
    is_suppressed = Column(Boolean, default=False)
    suppression_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    incident = relationship("Incident", back_populates="incident_alarms")
    alarm = relationship("Alarm", back_populates="incident_alarms")

    def __repr__(self):
        return f"<IncidentAlarm incident={self.incident_id} alarm={self.alarm_id}>"


class TimelineEvent(Base):
    """Timeline events within an incident."""

    __tablename__ = "timeline_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), ForeignKey("incidents.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    device_id = Column(String(36), ForeignKey("devices.id"))
    device_hostname = Column(String(255))
    event_type = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    alarm_id = Column(String(36), ForeignKey("alarms.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    incident = relationship("Incident", back_populates="timeline_events")

    def __repr__(self):
        return f"<TimelineEvent {self.event_type} at {self.timestamp}>"
