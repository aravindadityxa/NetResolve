"""Topology management service."""

from typing import List, Optional, Dict, Set
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.device import Device, Interface, Link


class TopologyService:
    """Service for topology operations and analysis."""

    @staticmethod
    def build_device_map(db: Session) -> Dict[str, Device]:
        """Build a map of hostname to device."""
        devices = db.query(Device).all()
        return {d.hostname: d for d in devices}

    @staticmethod
    def build_interface_map(db: Session) -> Dict[str, Interface]:
        """Build a map of interface ID to interface."""
        interfaces = db.query(Interface).all()
        return {i.id: i for i in interfaces}

    @staticmethod
    def get_device_links(db: Session, device_id: str) -> List[Link]:
        """Get all links connected to a device's interfaces."""
        interfaces = db.query(Interface).filter(Interface.device_id == device_id).all()
        interface_ids = [i.id for i in interfaces]

        links = db.query(Link).filter(
            (Link.source_interface_id.in_(interface_ids))
            | (Link.target_interface_id.in_(interface_ids))
        ).all()

        return links

    @staticmethod
    def get_upstream_device(db: Session, device_id: str) -> Optional[Device]:
        """Get upstream device(s) for a device."""
        # Get all interfaces for this device
        interfaces = db.query(Interface).filter(Interface.device_id == device_id).all()
        interface_ids = [i.id for i in interfaces]

        # Find links where this device is target
        links = db.query(Link).filter(Link.target_interface_id.in_(interface_ids)).all()

        if not links:
            return None

        # Get source interface and its device
        upstream_devices = []
        for link in links:
            source_iface = (
                db.query(Interface)
                .filter(Interface.id == link.source_interface_id)
                .first()
            )
            if source_iface:
                upstream_devices.append(source_iface.device)

        return upstream_devices[0] if upstream_devices else None

    @staticmethod
    def get_downstream_devices(db: Session, device_id: str) -> List[Device]:
        """Get all downstream devices (devices that depend on this device)."""
        # Get all interfaces for this device
        interfaces = db.query(Interface).filter(Interface.device_id == device_id).all()
        interface_ids = [i.id for i in interfaces]

        # Find links where this device is source
        links = db.query(Link).filter(Link.source_interface_id.in_(interface_ids)).all()

        # Get target interfaces and their devices
        downstream_devices = []
        for link in links:
            target_iface = (
                db.query(Interface)
                .filter(Interface.id == link.target_interface_id)
                .first()
            )
            if target_iface:
                downstream_devices.append(target_iface.device)

        return downstream_devices

    @staticmethod
    def get_blast_radius(db: Session, root_device_id: str) -> Set[str]:
        """Calculate blast radius: all devices affected downstream."""
        affected = set()
        to_check = [root_device_id]

        while to_check:
            current_device_id = to_check.pop(0)
            if current_device_id in affected:
                continue

            affected.add(current_device_id)

            downstream = TopologyService.get_downstream_devices(db, current_device_id)
            for device in downstream:
                if device.id not in affected:
                    to_check.append(device.id)

        # Don't count the root cause device itself
        affected.discard(root_device_id)
        return affected

    @staticmethod
    def get_path_to_device(db: Session, source_id: str, target_id: str) -> Optional[List[str]]:
        """
        Find a path between two devices using BFS.
        Returns list of device IDs from source to target.
        """
        if source_id == target_id:
            return [source_id]

        visited = set()
        queue = [(source_id, [source_id])]

        while queue:
            current_id, path = queue.pop(0)

            if current_id in visited:
                continue

            visited.add(current_id)

            # Check downstream neighbors
            downstream = TopologyService.get_downstream_devices(db, current_id)
            for neighbor in downstream:
                if neighbor.id == target_id:
                    return path + [target_id]

                if neighbor.id not in visited:
                    queue.append((neighbor.id, path + [neighbor.id]))

        return None

    @staticmethod
    def is_downstream(db: Session, root_id: str, device_id: str) -> bool:
        """Check if device_id is downstream of root_id."""
        blast_radius = TopologyService.get_blast_radius(db, root_id)
        return device_id in blast_radius

    @staticmethod
    def get_impacted_services(db: Session, affected_device_ids: List[str]) -> Dict[str, List[str]]:
        """
        Map affected devices to potential services.
        This is a simplified version; in production, you'd query a service registry.
        """
        service_map = {}
        for device_id in affected_device_ids:
            device = db.query(Device).filter(Device.id == device_id).first()
            if device:
                # Simple heuristic: device type hints at services
                if "router" in device.device_type.value.lower():
                    service_map.setdefault(device_id, []).append("routing")
                if "switch" in device.device_type.value.lower():
                    service_map.setdefault(device_id, []).append("switching")
                service_map.setdefault(device_id, []).append("connectivity")

        return service_map

    @staticmethod
    def get_topology_snapshot(db: Session) -> Dict:
        """Get current topology as a dictionary."""
        devices = db.query(Device).all()
        links = db.query(Link).all()

        device_list = [
            {
                "id": d.id,
                "hostname": d.hostname,
                "type": d.device_type.value,
                "ip": d.ip_address,
                "status": d.status,
            }
            for d in devices
        ]

        link_list = [
            {
                "id": l.id,
                "source_interface": l.source_interface_id,
                "target_interface": l.target_interface_id,
                "status": l.status,
            }
            for l in links
        ]

        return {"devices": device_list, "links": link_list, "timestamp": datetime.utcnow().isoformat()}
