"""Device management service."""

from typing import List, Optional
from sqlalchemy.orm import Session
import uuid

from app.core.logging import logger
from app.models.device import Device, Interface, Link
from app.schemas.device import DeviceSchema, InterfaceSchema


class DeviceService:
    """Service for managing network devices."""

    @staticmethod
    def get_device(db: Session, device_id: str) -> Optional[Device]:
        """Get a device by ID."""
        return db.query(Device).filter(Device.id == device_id).first()

    @staticmethod
    def get_device_by_hostname(db: Session, hostname: str) -> Optional[Device]:
        """Get a device by hostname."""
        return db.query(Device).filter(Device.hostname == hostname).first()

    @staticmethod
    def list_devices(db: Session, skip: int = 0, limit: int = 100) -> List[Device]:
        """List all devices with pagination."""
        return db.query(Device).offset(skip).limit(limit).all()

    @staticmethod
    def create_device(db: Session, hostname: str, device_type: str, ip_address: str, description: Optional[str] = None) -> Device:
        """Create a new device."""
        device = Device(
            id=str(uuid.uuid4()),
            hostname=hostname,
            device_type=device_type,
            ip_address=ip_address,
            description=description,
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        logger.info(f"Created device: {hostname} ({device.id})")
        return device

    @staticmethod
    def update_device_status(db: Session, device_id: str, status: str) -> Optional[Device]:
        """Update device status."""
        device = db.query(Device).filter(Device.id == device_id).first()
        if device:
            device.status = status
            db.commit()
            db.refresh(device)
        return device

    @staticmethod
    def get_device_interfaces(db: Session, device_id: str) -> List[Interface]:
        """Get all interfaces for a device."""
        return db.query(Interface).filter(Interface.device_id == device_id).all()

    @staticmethod
    def create_interface(
        db: Session,
        device_id: str,
        name: str,
        interface_type: str,
        speed_mbps: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> Interface:
        """Create a new interface."""
        interface = Interface(
            id=str(uuid.uuid4()),
            name=name,
            device_id=device_id,
            interface_type=interface_type,
            speed_mbps=speed_mbps,
            ip_address=ip_address,
        )
        db.add(interface)
        db.commit()
        db.refresh(interface)
        return interface

    @staticmethod
    def get_device_count(db: Session) -> int:
        """Get total device count."""
        return db.query(Device).count()
