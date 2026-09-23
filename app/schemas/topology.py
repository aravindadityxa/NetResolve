"""Pydantic schemas for network topology."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class TopologyNodeSchema(BaseModel):
    """Network topology node (device)."""
    id: str
    hostname: str
    device_type: str
    status: str
    affected: bool = False
    is_root_cause: bool = False


class TopologyLinkSchema(BaseModel):
    """Network topology link."""
    id: str
    source_id: str
    target_id: str
    status: str
    affected: bool = False


class TopologyGraphSchema(BaseModel):
    """Complete topology graph."""
    nodes: List[TopologyNodeSchema]
    links: List[TopologyLinkSchema]


class DependencySchema(BaseModel):
    """Dependency relationship."""
    source_device_id: str
    target_device_id: str
    dependency_type: str  # "upstream", "downstream", "peer"
    criticality: str  # "critical", "high", "medium", "low"


class BlastRadiusSchema(BaseModel):
    """Impact/blast radius calculation."""
    root_cause_device_id: str
    affected_devices: List[str]
    affected_count: int
    affected_links: List[str]
    affected_services: Optional[List[str]] = None
    impact_score: float  # 0-1
