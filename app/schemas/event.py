"""Pydantic schemas for network events."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class NetworkEventSchema(BaseModel):
    """Raw network event from simulator or collection source."""
    event_id: str = Field(..., description="Unique event ID")
    timestamp: datetime = Field(..., description="Event timestamp")
    source: str = Field(..., description="Event source (simulator, snmp, syslog, etc.)")
    device_id: str = Field(..., description="Originating device ID")
    device_hostname: str = Field(..., description="Device hostname")
    event_type: str = Field(..., description="Event type")
    interface_id: Optional[str] = Field(None, description="Affected interface")
    severity: str = Field(default="informational", description="Event severity")
    message: str = Field(..., description="Event message")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw event data")

    class Config:
        from_attributes = True


class EventStatisticsSchema(BaseModel):
    """Event statistics."""
    total_events: int
    events_by_source: Dict[str, int]
    events_by_device: Dict[str, int]
    events_by_type: Dict[str, int]
