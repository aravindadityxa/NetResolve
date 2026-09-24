"""Topology endpoints."""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from app.core.logging import logger
from app.core.database import SessionLocal
from app.models.device import Device, Interface, Link
from app.schemas.device import DeviceResponse, LinkResponse
from app.services.topology_service import TopologyService

router = APIRouter(tags=["Topology"])


@router.get("/topology")
async def get_topology() -> Dict[str, Any]:
    """Get network topology."""
    try:
        db = SessionLocal()

        # Get all devices
        devices = db.query(Device).all()
        device_list = [
            {
                "id": d.id,
                "name": d.name,
                "type": d.device_type,
                "status": d.status,
            }
            for d in devices
        ]

        # Get all links
        links = db.query(Link).all()
        link_list = [
            {
                "source_interface_id": l.source_interface_id,
                "target_interface_id": l.target_interface_id,
                "status": l.status,
            }
            for l in links
        ]

        # Get all interfaces
        interfaces = db.query(Interface).all()
        interface_dict = {
            i.id: {
                "id": i.id,
                "device_id": i.device_id,
                "name": i.name,
                "status": i.status,
                "speed": i.speed,
            }
            for i in interfaces
        }

        db.close()

        return {
            "devices": device_list,
            "links": link_list,
            "interfaces": interface_dict,
            "device_count": len(device_list),
            "link_count": len(link_list),
            "interface_count": len(interface_dict),
        }
    except Exception as e:
        logger.error(f"Error getting topology: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topology/summary")
async def get_topology_summary() -> Dict[str, Any]:
    """Get topology summary statistics."""
    try:
        db = SessionLocal()

        total_devices = db.query(Device).count()
        up_devices = db.query(Device).filter(Device.status == "up").count()
        down_devices = db.query(Device).filter(Device.status == "down").count()

        total_links = db.query(Link).count()
        up_links = db.query(Link).filter(Link.status == "up").count()

        total_interfaces = db.query(Interface).count()
        up_interfaces = db.query(Interface).filter(Interface.status == "up").count()

        db.close()

        return {
            "devices": {
                "total": total_devices,
                "up": up_devices,
                "down": down_devices,
            },
            "links": {
                "total": total_links,
                "up": up_links,
                "down": total_links - up_links,
            },
            "interfaces": {
                "total": total_interfaces,
                "up": up_interfaces,
                "down": total_interfaces - up_interfaces,
            },
            "health_score": (up_devices / total_devices * 100) if total_devices > 0 else 100,
        }
    except Exception as e:
        logger.error(f"Error getting topology summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topology/paths/{source_device_id}/{target_device_id}")
async def get_topology_path(source_device_id: str, target_device_id: str):
    """Get path between two devices."""
    try:
        db = SessionLocal()
        service = TopologyService(db)

        path = service.find_path(source_device_id, target_device_id)
        db.close()

        if not path:
            raise HTTPException(status_code=404, detail="No path found")

        return {
            "source": source_device_id,
            "target": target_device_id,
            "path": path,
            "hops": len(path) - 1,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding path: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topology/dependencies/{device_id}")
async def get_device_dependencies(device_id: str):
    """Get device dependencies (upstream and downstream)."""
    try:
        db = SessionLocal()
        service = TopologyService(db)

        upstream = service.get_upstream_device(device_id)
        downstream = service.get_downstream_devices(device_id)

        db.close()

        return {
            "device_id": device_id,
            "upstream_device": upstream,
            "downstream_devices": downstream,
            "dependency_count": len(downstream),
        }
    except Exception as e:
        logger.error(f"Error getting dependencies: {e}")
        raise HTTPException(status_code=500, detail=str(e))
