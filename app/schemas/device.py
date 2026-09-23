"""Pydantic schemas for network devices."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.core.constants import DeviceType, InterfaceType


class InterfaceSchema(BaseModel):
    """Network interface representation."""
    id: str = Field(..., description="Interface ID")
    name: str = Field(..., description="Interface name")
    device_id: str = Field(..., description="Parent device ID")
    interface_type: InterfaceType = Field(..., description="Interface type")
    status: str = Field(default="up", description="Interface operational status")
    speed_mbps: Optional[int] = Field(None, description="Interface speed in Mbps")
    mtu: int = Field(default=1500, description="Maximum transmission unit")
    ip_address: Optional[str] = Field(None, description="Interface IP address")
    description: Optional[str] = None

    class Config:
        from_attributes = True


class LinkSchema(BaseModel):
    """Network link between two interfaces."""
    id: str = Field(..., description="Link ID")
    source_interface_id: str = Field(..., description="Source interface")
    target_interface_id: str = Field(..., description="Target interface")
    status: str = Field(default="up", description="Link operational status")

    class Config:
        from_attributes = True


class DeviceSchema(BaseModel):
    """Network device representation."""
    id: str = Field(..., description="Device ID")
    hostname: str = Field(..., description="Device hostname")
    device_type: DeviceType = Field(..., description="Device type")
    ip_address: str = Field(..., description="Management IP address")
    status: str = Field(default="up", description="Device operational status")
    description: Optional[str] = None
    interfaces: Optional[List[InterfaceSchema]] = None

    class Config:
        from_attributes = True


class DeviceStatusSchema(BaseModel):
    """Device operational status snapshot."""
    device_id: str
    hostname: str
    status: str
    last_seen: datetime
    reachable: bool
    interfaces_up: int
    interfaces_down: int
    interfaces_degraded: int

    class Config:
        from_attributes = True
