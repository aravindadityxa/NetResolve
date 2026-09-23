"""Database models for network events."""

from sqlalchemy import Column, String, DateTime, Text, JSON
from datetime import datetime
import uuid

from app.core.database import Base


class NetworkEvent(Base):
    """Raw network event from any source."""

    __tablename__ = "network_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String(255), unique=True, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    source = Column(String(100), nullable=False, index=True)
    device_id = Column(String(36), nullable=False, index=True)
    device_hostname = Column(String(255), nullable=False)
    event_type = Column(String(100), nullable=False, index=True)
    interface_id = Column(String(36))
    severity = Column(String(50), default="informational")
    message = Column(Text, nullable=False)
    raw_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<NetworkEvent {self.event_type} from {self.device_hostname}>"
