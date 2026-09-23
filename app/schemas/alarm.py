"""Pydantic schemas for alarms."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from app.core.constants import AlarmSeverity, AlarmType, AlarmStatus


class AlarmSchema(BaseModel):
    """Alarm representation."""
    id: Optional[UUID] = None
    event_id: str = Field(..., description="Source event ID")
    timestamp: datetime = Field(..., description="Alarm generation timestamp")
    device_id: str = Field(..., description="Affected device ID")
    device_hostname: str = Field(..., description="Device hostname")
    interface_id: Optional[str] = Field(None, description="Affected interface")
    alarm_type: AlarmType = Field(..., description="Alarm type")
    severity: AlarmSeverity = Field(..., description="Alarm severity")
    status: AlarmStatus = Field(default=AlarmStatus.OPEN, description="Alarm status")
    message: str = Field(..., description="Alarm message")
    source: str = Field(..., description="Event source (simulator, snmp, syslog, etc.)")
    correlation_id: Optional[str] = Field(None, description="Correlation group ID")
    parent_alarm_id: Optional[UUID] = Field(None, description="Parent alarm if secondary")
    probable_root_cause: Optional[bool] = Field(None, description="Is this the root cause?")
    confidence: Optional[float] = Field(None, description="RCA confidence 0-1")
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    occurrence_count: int = Field(default=1, description="How many times this alarm occurred")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Additional raw event data")

    class Config:
        from_attributes = True


class AlarmCreateSchema(BaseModel):
    """Schema for creating new alarms."""
    event_id: str
    timestamp: datetime
    device_id: str
    device_hostname: str
    interface_id: Optional[str] = None
    alarm_type: AlarmType
    severity: AlarmSeverity
    message: str
    source: str
    raw_data: Optional[Dict[str, Any]] = None


class AlarmUpdateSchema(BaseModel):
    """Schema for updating alarms."""
    status: Optional[AlarmStatus] = None
    confidence: Optional[float] = None
    probable_root_cause: Optional[bool] = None
    occurrence_count: Optional[int] = None


class AlarmStatisticsSchema(BaseModel):
    """Alarm statistics."""
    total_alarms: int
    open_alarms: int
    suppressed_alarms: int
    resolved_alarms: int
    critical_count: int
    major_count: int
    minor_count: int
    by_device: Dict[str, int]
    by_type: Dict[str, int]
