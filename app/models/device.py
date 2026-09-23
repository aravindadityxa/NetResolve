"""Database models for network devices."""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base
from app.core.constants import DeviceType, InterfaceType


class Device(Base):
    """Network device model."""

    __tablename__ = "devices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hostname = Column(String(255), unique=True, nullable=False, index=True)
    device_type = Column(Enum(DeviceType), nullable=False)
    ip_address = Column(String(45), nullable=False)
    status = Column(String(50), default="up", nullable=False)
    description = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)

    # Relationships
    interfaces = relationship("Interface", back_populates="device", cascade="all, delete-orphan")
    alarms = relationship("Alarm", back_populates="device")

    def __repr__(self):
        return f"<Device {self.hostname} ({self.device_type})>"


class Interface(Base):
    """Network interface model."""

    __tablename__ = "interfaces"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    device_id = Column(String(36), ForeignKey("devices.id"), nullable=False, index=True)
    interface_type = Column(Enum(InterfaceType), nullable=False)
    status = Column(String(50), default="up", nullable=False)
    speed_mbps = Column(Integer)
    mtu = Column(Integer, default=1500)
    ip_address = Column(String(45))
    description = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    device = relationship("Device", back_populates="interfaces")
    source_links = relationship(
        "Link",
        foreign_keys="Link.source_interface_id",
        back_populates="source_interface",
    )
    target_links = relationship(
        "Link",
        foreign_keys="Link.target_interface_id",
        back_populates="target_interface",
    )

    def __repr__(self):
        return f"<Interface {self.name} on {self.device_id}>"


class Link(Base):
    """Network link between two interfaces."""

    __tablename__ = "links"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_interface_id = Column(String(36), ForeignKey("interfaces.id"), nullable=False)
    target_interface_id = Column(String(36), ForeignKey("interfaces.id"), nullable=False)
    status = Column(String(50), default="up", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    source_interface = relationship(
        "Interface",
        foreign_keys=[source_interface_id],
        back_populates="source_links",
    )
    target_interface = relationship(
        "Interface",
        foreign_keys=[target_interface_id],
        back_populates="target_links",
    )

    def __repr__(self):
        return f"<Link {self.source_interface_id} -> {self.target_interface_id}>"
