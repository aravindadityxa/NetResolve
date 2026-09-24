"""Device and topology endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import List

from app.core.logging import logger
from app.core.database import SessionLocal
from app.models.device import Device, Interface
from app.schemas.device import DeviceResponse, InterfaceResponse
from app.services.device_service import DeviceService
from app.services.topology_service import TopologyService

router = APIRouter(tags=["Devices"])


@router.get("/devices", response_model=List[DeviceResponse])
async def list_devices(
    status: str = Query(None, description="Filter by device status"),
):
    """List all devices."""
    try:
        db = SessionLocal()
        query = db.query(Device)

        if status:
            query = query.filter(Device.status == status)

        devices = query.all()
        db.close()

        return [DeviceResponse.from_orm(d) for d in devices]
    except Exception as e:
        logger.error(f"Error listing devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: str):
    """Get device details."""
    try:
        db = SessionLocal()
        device = db.query(Device).filter(Device.id == device_id).first()
        db.close()

        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        return DeviceResponse.from_orm(device)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices/{device_id}/interfaces", response_model=List[InterfaceResponse])
async def get_device_interfaces(device_id: str):
    """Get device interfaces."""
    try:
        db = SessionLocal()
        interfaces = db.query(Interface).filter(Interface.device_id == device_id).all()
        db.close()

        return [InterfaceResponse.from_orm(i) for i in interfaces]
    except Exception as e:
        logger.error(f"Error getting interfaces for {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices/{device_id}/blast-radius")
async def get_blast_radius(device_id: str):
    """Calculate blast radius for device failure."""
    try:
        db = SessionLocal()
        service = TopologyService(db)

        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            db.close()
            raise HTTPException(status_code=404, detail="Device not found")

        downstream = service.get_downstream_devices(device_id)
        affected_count = len(downstream)

        db.close()

        return {
            "device_id": device_id,
            "device_name": device.name,
            "affected_devices": affected_count,
            "affected_device_ids": downstream,
            "impact_level": "high" if affected_count > 3 else "medium" if affected_count > 1 else "low",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating blast radius: {e}")
        raise HTTPException(status_code=500, detail=str(e))
