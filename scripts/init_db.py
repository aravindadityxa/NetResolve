#!/usr/bin/env python3
"""Initialize the database with sample topology."""

import sys
import uuid
from datetime import datetime

# Add app to path
sys.path.insert(0, str(__file__).replace("scripts/init_db.py", ""))

from app.core.database import init_db, SessionLocal
from app.core.logging import logger
from app.core.constants import DeviceType, InterfaceType
from app.models import Device, Interface, Link
from app.core.constants import DeviceType, InterfaceType as InterfaceTypeEnum


def create_sample_topology():
    """Create sample network topology."""
    logger.info("Creating sample network topology...")

    db = SessionLocal()

    # Clear existing data
    db.query(Link).delete()
    db.query(Interface).delete()
    db.query(Device).delete()
    db.commit()

    # Create devices
    devices = [
        Device(
            id=str(uuid.uuid4()),
            hostname="CORE-R1",
            device_type=DeviceType.CORE_ROUTER,
            ip_address="10.0.0.1",
            description="Core router 1",
        ),
        Device(
            id=str(uuid.uuid4()),
            hostname="DIST-R1",
            device_type=DeviceType.DISTRIBUTION_ROUTER,
            ip_address="10.0.1.1",
            description="Distribution router 1",
        ),
        Device(
            id=str(uuid.uuid4()),
            hostname="DIST-R2",
            device_type=DeviceType.DISTRIBUTION_ROUTER,
            ip_address="10.0.2.1",
            description="Distribution router 2",
        ),
        Device(
            id=str(uuid.uuid4()),
            hostname="ACCESS-SW1",
            device_type=DeviceType.ACCESS_SWITCH,
            ip_address="10.1.0.1",
            description="Access switch 1",
        ),
        Device(
            id=str(uuid.uuid4()),
            hostname="ACCESS-SW2",
            device_type=DeviceType.ACCESS_SWITCH,
            ip_address="10.1.1.1",
            description="Access switch 2",
        ),
        Device(
            id=str(uuid.uuid4()),
            hostname="ACCESS-SW3",
            device_type=DeviceType.ACCESS_SWITCH,
            ip_address="10.1.2.1",
            description="Access switch 3",
        ),
        Device(
            id=str(uuid.uuid4()),
            hostname="ACCESS-SW4",
            device_type=DeviceType.ACCESS_SWITCH,
            ip_address="10.1.3.1",
            description="Access switch 4",
        ),
        Device(
            id=str(uuid.uuid4()),
            hostname="DIST-R1",
            device_type=DeviceType.DISTRIBUTION_ROUTER,
            ip_address="10.0.1.1",
            description="Distribution router 1",
        ),
        Device(
            id=str(uuid.uuid4()),
            hostname="DIST-R2",
            device_type=DeviceType.DISTRIBUTION_ROUTER,
            ip_address="10.0.2.1",
            description="Distribution router 2",
        ),
        Device(
            id=str(uuid.uuid4()),
            hostname="ACCESS-SW1",
            device_type=DeviceType.ACCESS_SWITCH,
            ip_address="10.1.0.1",
            description="Access switch 1",
        ),
        Device(
            id=str(uuid.uuid4()),
            hostname="ACCESS-SW2",
            device_type=DeviceType.ACCESS_SWITCH,
            ip_address="10.1.1.1",
            description="Access switch 2",
        ),
        Device(
            id=str(uuid.uuid4()),
            hostname="ACCESS-SW3",
            device_type=DeviceType.ACCESS_SWITCH,
            ip_address="10.1.2.1",
            description="Access switch 3",
        ),
        Device(
            id=str(uuid.uuid4()),
            hostname="ACCESS-SW4",
            device_type=DeviceType.ACCESS_SWITCH,
            ip_address="10.1.3.1",
            description="Access switch 4",
        ),
    ]

    for device in devices:
        db.add(device)

    db.commit()

    # Create interfaces
    interfaces = []
    device_map = {d.hostname: d for d in devices}

    for hostname, device in device_map.items():
        for i in range(1, 5):
            iface = Interface(
                id=str(uuid.uuid4()),
                name=f"GigabitEthernet0/{i}",
                device_id=device.id,
                interface_type=InterfaceTypeEnum.GIGABIT_ETHERNET,
                speed_mbps=1000,
                ip_address=f"{device.ip_address.rsplit('.', 1)[0]}.{i}",
            )
            interfaces.append(iface)
            db.add(iface)

    db.commit()

    # Create links
    interface_map = {f"{i.device_id}:{i.name}": i for i in interfaces}

    # Sample topology connections
    connections = [
        # CORE-R1 to DIST routers
        ("CORE-R1", "GigabitEthernet0/1", "DIST-R1", "GigabitEthernet0/1"),
        ("CORE-R1", "GigabitEthernet0/2", "DIST-R2", "GigabitEthernet0/1"),
        # DIST-R1 to Access switches
        ("DIST-R1", "GigabitEthernet0/2", "ACCESS-SW1", "GigabitEthernet0/1"),
        ("DIST-R1", "GigabitEthernet0/3", "ACCESS-SW2", "GigabitEthernet0/1"),
        # DIST-R2 to Access switches
        ("DIST-R2", "GigabitEthernet0/2", "ACCESS-SW3", "GigabitEthernet0/1"),
        ("DIST-R2", "GigabitEthernet0/3", "ACCESS-SW4", "GigabitEthernet0/1"),
    ]

    for src_host, src_iface, tgt_host, tgt_iface in connections:
        src_device = device_map[src_host]
        tgt_device = device_map[tgt_host]

        src_interface = next(
            (i for i in interfaces if i.device_id == src_device.id and i.name == src_iface),
            None,
        )
        tgt_interface = next(
            (i for i in interfaces if i.device_id == tgt_device.id and i.name == tgt_iface),
            None,
        )

        if src_interface and tgt_interface:
            link = Link(
                id=str(uuid.uuid4()),
                source_interface_id=src_interface.id,
                target_interface_id=tgt_interface.id,
            )
            db.add(link)

    db.commit()

    logger.info(f"✓ Created {len(devices)} devices")
    logger.info(f"✓ Created {len(interfaces)} interfaces")
    logger.info(f"✓ Created {len(connections)} links")

    db.close()


if __name__ == "__main__":
    logger.info("Initializing NetResolve database...")
    init_db()
    logger.info("Database schema created")
    create_sample_topology()
    logger.info("✓ Database initialization complete!")
