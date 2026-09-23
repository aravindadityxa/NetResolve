"""Database models for network topology."""

from sqlalchemy import Column, String, DateTime, JSON, Integer
from datetime import datetime
import uuid

from app.core.database import Base


class TopologySnapshot(Base):
    """Snapshot of the network topology at a point in time."""

    __tablename__ = "topology_snapshots"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    devices = Column(JSON, nullable=False)  # List of device objects
    links = Column(JSON, nullable=False)  # List of link objects
    interfaces = Column(JSON, nullable=False)  # List of interface objects
    dependencies = Column(JSON)  # Dependency relationships
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<TopologySnapshot {self.timestamp}>"
