"""Simulated network topology definition."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class DeviceRole(str, Enum):
    """Device roles in the network."""
    CORE = "core"
    DISTRIBUTION = "distribution"
    ACCESS = "access"


@dataclass
class SimulatedInterface:
    """Simulated network interface."""
    name: str
    speed_mbps: int = 1000
    mtu: int = 1500
    status: str = "up"
    ip_address: Optional[str] = None


@dataclass
class SimulatedLink:
    """Link between two interfaces."""
    source_device: str
    source_interface: str
    target_device: str
    target_interface: str
    status: str = "up"


@dataclass
class SimulatedDevice:
    """Simulated network device."""
    hostname: str
    ip_address: str
    role: DeviceRole
    interfaces: Dict[str, SimulatedInterface] = field(default_factory=dict)
    status: str = "up"
    description: str = ""


class SimulatedTopology:
    """
    Simulated network topology.
    
    Structure:
                      CORE-R1
                     /       \
                DIST-R1     DIST-R2
                 /  \        /  \
            ACC-SW1 ACC-SW2 ACC-SW3 ACC-SW4
    """

    def __init__(self):
        """Initialize simulated topology."""
        self.devices: Dict[str, SimulatedDevice] = {}
        self.links: Dict[str, SimulatedLink] = {}
        self._initialize_topology()

    def _initialize_topology(self):
        """Create the simulated network topology."""
        
        # Core Layer
        self.devices["CORE-R1"] = SimulatedDevice(
            hostname="CORE-R1",
            ip_address="10.0.0.1",
            role=DeviceRole.CORE,
            description="Core Router 1 - Primary backbone",
            interfaces={
                "GigabitEthernet0/1": SimulatedInterface(
                    name="GigabitEthernet0/1",
                    ip_address="10.0.0.1",
                ),
                "GigabitEthernet0/2": SimulatedInterface(
                    name="GigabitEthernet0/2",
                    ip_address="10.0.0.2",
                ),
                "Loopback0": SimulatedInterface(
                    name="Loopback0",
                    ip_address="10.0.0.254",
                ),
            },
        )

        # Distribution Layer
        self.devices["DIST-R1"] = SimulatedDevice(
            hostname="DIST-R1",
            ip_address="10.0.1.1",
            role=DeviceRole.DISTRIBUTION,
            description="Distribution Router 1 - Regional aggregation",
            interfaces={
                "GigabitEthernet0/1": SimulatedInterface(
                    name="GigabitEthernet0/1",
                    ip_address="10.0.1.1",
                ),
                "GigabitEthernet0/2": SimulatedInterface(
                    name="GigabitEthernet0/2",
                    ip_address="10.0.1.2",
                ),
                "GigabitEthernet0/3": SimulatedInterface(
                    name="GigabitEthernet0/3",
                    ip_address="10.0.1.3",
                ),
                "Loopback0": SimulatedInterface(
                    name="Loopback0",
                    ip_address="10.0.1.254",
                ),
            },
        )

        self.devices["DIST-R2"] = SimulatedDevice(
            hostname="DIST-R2",
            ip_address="10.0.2.1",
            role=DeviceRole.DISTRIBUTION,
            description="Distribution Router 2 - Regional aggregation",
            interfaces={
                "GigabitEthernet0/1": SimulatedInterface(
                    name="GigabitEthernet0/1",
                    ip_address="10.0.2.1",
                ),
                "GigabitEthernet0/2": SimulatedInterface(
                    name="GigabitEthernet0/2",
                    ip_address="10.0.2.2",
                ),
                "GigabitEthernet0/3": SimulatedInterface(
                    name="GigabitEthernet0/3",
                    ip_address="10.0.2.3",
                ),
                "Loopback0": SimulatedInterface(
                    name="Loopback0",
                    ip_address="10.0.2.254",
                ),
            },
        )

        # Access Layer
        for i, (hostname, ip) in enumerate([
            ("ACCESS-SW1", "10.1.0.1"),
            ("ACCESS-SW2", "10.1.1.1"),
            ("ACCESS-SW3", "10.1.2.1"),
            ("ACCESS-SW4", "10.1.3.1"),
        ], 1):
            self.devices[hostname] = SimulatedDevice(
                hostname=hostname,
                ip_address=ip,
                role=DeviceRole.ACCESS,
                description=f"Access Switch {i} - End user access",
                interfaces={
                    "GigabitEthernet0/1": SimulatedInterface(
                        name="GigabitEthernet0/1",
                        ip_address=f"{ip.rsplit('.', 1)[0]}.1",
                    ),
                    "GigabitEthernet0/2": SimulatedInterface(
                        name="GigabitEthernet0/2",
                        ip_address=f"{ip.rsplit('.', 1)[0]}.2",
                    ),
                    "GigabitEthernet0/3": SimulatedInterface(
                        name="GigabitEthernet0/3",
                        ip_address=f"{ip.rsplit('.', 1)[0]}.3",
                    ),
                },
            )

        # Create links
        link_definitions = [
            # Core to Distribution
            ("CORE-R1", "GigabitEthernet0/1", "DIST-R1", "GigabitEthernet0/1"),
            ("CORE-R1", "GigabitEthernet0/2", "DIST-R2", "GigabitEthernet0/1"),
            # Distribution to Access
            ("DIST-R1", "GigabitEthernet0/2", "ACCESS-SW1", "GigabitEthernet0/1"),
            ("DIST-R1", "GigabitEthernet0/3", "ACCESS-SW2", "GigabitEthernet0/1"),
            ("DIST-R2", "GigabitEthernet0/2", "ACCESS-SW3", "GigabitEthernet0/1"),
            ("DIST-R2", "GigabitEthernet0/3", "ACCESS-SW4", "GigabitEthernet0/1"),
        ]

        for src_dev, src_iface, tgt_dev, tgt_iface in link_definitions:
            link_id = f"{src_dev}:{src_iface}--{tgt_dev}:{tgt_iface}"
            self.links[link_id] = SimulatedLink(
                source_device=src_dev,
                source_interface=src_iface,
                target_device=tgt_dev,
                target_interface=tgt_iface,
            )

    def get_device(self, hostname: str) -> Optional[SimulatedDevice]:
        """Get a device by hostname."""
        return self.devices.get(hostname)

    def get_downstream_devices(self, hostname: str) -> List[str]:
        """Get all downstream devices (affected by this device's failure)."""
        downstream = []
        visited = set()

        def traverse(device: str):
            if device in visited:
                return
            visited.add(device)

            for link in self.links.values():
                if link.source_device == device and link.target_device not in visited:
                    downstream.append(link.target_device)
                    traverse(link.target_device)

        traverse(hostname)
        return downstream

    def get_upstream_device(self, hostname: str) -> Optional[str]:
        """Get the upstream device."""
        for link in self.links.values():
            if link.target_device == hostname:
                return link.source_device
        return None

    def set_device_status(self, hostname: str, status: str):
        """Change device status (up/down)."""
        if hostname in self.devices:
            self.devices[hostname].status = status

    def set_interface_status(self, hostname: str, interface: str, status: str):
        """Change interface status."""
        if hostname in self.devices:
            device = self.devices[hostname]
            if interface in device.interfaces:
                device.interfaces[interface].status = status

    def set_link_status(self, source_device: str, source_iface: str, 
                        target_device: str, target_iface: str, status: str):
        """Change link status."""
        link_id = f"{source_device}:{source_iface}--{target_device}:{target_iface}"
        if link_id in self.links:
            self.links[link_id].status = status

    def get_all_devices(self) -> List[SimulatedDevice]:
        """Get all devices."""
        return list(self.devices.values())

    def get_all_links(self) -> List[SimulatedLink]:
        """Get all links."""
        return list(self.links.values())

    def get_topology_summary(self) -> dict:
        """Get topology summary."""
        return {
            "devices": {
                hostname: {
                    "ip": device.ip_address,
                    "role": device.role.value,
                    "status": device.status,
                    "interfaces": list(device.interfaces.keys()),
                }
                for hostname, device in self.devices.items()
            },
            "links": len(self.links),
            "layers": {
                "core": [h for h, d in self.devices.items() if d.role == DeviceRole.CORE],
                "distribution": [h for h, d in self.devices.items() if d.role == DeviceRole.DISTRIBUTION],
                "access": [h for h, d in self.devices.items() if d.role == DeviceRole.ACCESS],
            },
        }
