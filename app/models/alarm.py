"""Database models for alarms."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Boolean, Float, Integer, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base
from app.core.constants import AlarmSeverity, AlarmType, AlarmStatus


class Alarm(Base):
    """Alarm model."""

    __tablename__ = "alarms"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String(255), unique=True, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    device_id = Column(String(36), ForeignKey("devices.id"), nullable=False, index=True)
    device_hostname = Column(String(255), nullable=False)
    interface_id = Column(String(36), ForeignKey("interfaces.id"))
    alarm_type = Column(Enum(AlarmType), nullable=False, index=True)
    severity = Column(Enum(AlarmSeverity), nullable=False)
    status = Column(Enum(AlarmStatus), default=AlarmStatus.OPEN, index=True)
    message = Column(Text, nullable=False)
    source = Column(String(100), nullable=False)
    correlation_id = Column(String(36), index=True)
    parent_alarm_id = Column(String(36), ForeignKey("alarms.id"))
    probable_root_cause = Column(Boolean)
    confidence = Column(Float)  # 0-1
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    occurrence_count = Column(Integer, default=1)
    raw_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    device = relationship("Device", back_populates="alarms")
    interface = relationship("Interface")
    incident_alarms = relationship("IncidentAlarm", back_populates="alarm")

    def __repr__(self):
        return f"<Alarm {self.alarm_type} on {self.device_hostname}>"
