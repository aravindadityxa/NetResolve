"""Pydantic schemas for incidents."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

from app.core.constants import IncidentState


class TimelineEventSchema(BaseModel):
    """Single event in incident timeline."""
    timestamp: datetime
    device_id: str
    device_hostname: str
    event_type: str
    message: str
    alarm_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class IncidentSchema(BaseModel):
    """Incident representation."""
    id: Optional[UUID] = None
    state: IncidentState = Field(default=IncidentState.OPEN, description="Incident state")
    severity: str = Field(..., description="Incident severity")
    created_at: datetime = Field(..., description="Incident creation time")
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    root_cause_device_id: Optional[str] = Field(None, description="Root cause device")
    root_cause_interface_id: Optional[str] = Field(None, description="Root cause interface")
    root_cause_alarm_id: Optional[UUID] = Field(None, description="Root cause alarm")
    probable_root_cause: Optional[str] = Field(None, description="Root cause description")
    rca_confidence: Optional[float] = Field(None, description="RCA confidence 0-1")
    rca_reasoning: Optional[str] = Field(None, description="RCA reasoning/explanation")
    affected_devices: List[str] = Field(default_factory=list, description="List of affected device IDs")
    blast_radius: int = Field(default=0, description="Number of affected devices")
    affected_links: List[str] = Field(default_factory=list, description="List of affected link IDs")
    timeline: List[TimelineEventSchema] = Field(default_factory=list, description="Event timeline")
    related_alarms: List[UUID] = Field(default_factory=list, description="All related alarm IDs")
    suppressed_alarms: List[UUID] = Field(default_factory=list, description="Suppressed alarm IDs")
    suppression_count: int = Field(default=0, description="Number of suppressed alarms")
    mttd: Optional[float] = Field(None, description="Mean time to detect in seconds")
    mtti: Optional[float] = Field(None, description="Mean time to identify root cause in seconds")
    mttr: Optional[float] = Field(None, description="Mean time to resolve in seconds")
    extra_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    class Config:
        from_attributes = True


class IncidentDetailSchema(IncidentSchema):
    """Detailed incident view with full data."""
    pass


class IncidentCreateSchema(BaseModel):
    """Schema for creating incidents."""
    severity: str
    root_cause_device_id: Optional[str] = None


class IncidentUpdateSchema(BaseModel):
    """Schema for updating incidents."""
    state: Optional[IncidentState] = None
    root_cause_device_id: Optional[str] = None
    rca_confidence: Optional[float] = None
    rca_reasoning: Optional[str] = None


class IncidentSummarySchema(BaseModel):
    """Incident summary for list views."""
    id: UUID
    state: IncidentState
    severity: str
    created_at: datetime
    root_cause_device_id: Optional[str]
    blast_radius: int
    suppression_count: int
    rca_confidence: Optional[float]


class IncidentStatisticsSchema(BaseModel):
    """Incident statistics."""
    total_incidents: int
    open_incidents: int
    active_incidents: int
    resolved_incidents: int
    average_mttd_seconds: float
    average_mtti_seconds: float
    average_mttr_seconds: float
    by_severity: Dict[str, int]
    by_state: Dict[str, int]
