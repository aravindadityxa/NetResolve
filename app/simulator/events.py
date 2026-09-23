"""Event generation for network simulator."""

from datetime import datetime, timedelta
from typing import List, Optional
from dataclasses import dataclass
import uuid
import random

from app.core.constants import AlarmType, AlarmSeverity
from app.simulator.topology import SimulatedTopology


@dataclass
class SimulatedEvent:
    """Simulated network event."""
    event_id: str
    timestamp: datetime
    device_id: str
    device_hostname: str
    event_type: str
    interface_id: Optional[str]
    severity: str
    message: str
    source: str = "simulator"


class EventGenerator:
    """Generate realistic network events from simulator topology."""

    def __init__(self, topology: SimulatedTopology):
        """Initialize event generator."""
        self.topology = topology
        self.event_counter = 0

    def _next_event_id(self) -> str:
        """Generate unique event ID."""
        self.event_counter += 1
        return f"SIM-{datetime.utcnow().timestamp():.0f}-{self.event_counter}"

    def _get_device_id(self, hostname: str) -> str:
        """Get device ID from hostname (simplified: use hostname as ID)."""
        return hostname

    # ============================================================================
    # Interface Events
    # ============================================================================

    def interface_down(
        self,
        hostname: str,
        interface_name: str,
        timestamp: Optional[datetime] = None,
    ) -> SimulatedEvent:
        """Generate interface down event."""
        if not timestamp:
            timestamp = datetime.utcnow()

        device = self.topology.get_device(hostname)
        if device:
            self.topology.set_interface_status(hostname, interface_name, "down")

        return SimulatedEvent(
            event_id=self._next_event_id(),
            timestamp=timestamp,
            device_id=self._get_device_id(hostname),
            device_hostname=hostname,
            event_type="interface_down",
            interface_id=interface_name,
            severity=AlarmSeverity.MAJOR.value,
            message=f"Interface {interface_name} on {hostname} changed to DOWN",
        )

    def interface_up(
        self,
        hostname: str,
        interface_name: str,
        timestamp: Optional[datetime] = None,
    ) -> SimulatedEvent:
        """Generate interface up event (recovery)."""
        if not timestamp:
            timestamp = datetime.utcnow()

        device = self.topology.get_device(hostname)
        if device:
            self.topology.set_interface_status(hostname, interface_name, "up")

        return SimulatedEvent(
            event_id=self._next_event_id(),
            timestamp=timestamp,
            device_id=self._get_device_id(hostname),
            device_hostname=hostname,
            event_type="interface_recovery",
            interface_id=interface_name,
            severity=AlarmSeverity.INFORMATIONAL.value,
            message=f"Interface {interface_name} on {hostname} changed to UP",
        )

    # ============================================================================
    # Device Events
    # ============================================================================

    def device_unreachable(
        self,
        hostname: str,
        timestamp: Optional[datetime] = None,
    ) -> SimulatedEvent:
        """Generate device unreachable event."""
        if not timestamp:
            timestamp = datetime.utcnow()

        device = self.topology.get_device(hostname)
        if device:
            self.topology.set_device_status(hostname, "down")

        return SimulatedEvent(
            event_id=self._next_event_id(),
            timestamp=timestamp,
            device_id=self._get_device_id(hostname),
            device_hostname=hostname,
            event_type="device_unreachable",
            interface_id=None,
            severity=AlarmSeverity.CRITICAL.value,
            message=f"Device {hostname} is UNREACHABLE - no response to SNMP polls",
        )

    def device_recovery(
        self,
        hostname: str,
        timestamp: Optional[datetime] = None,
    ) -> SimulatedEvent:
        """Generate device recovery event."""
        if not timestamp:
            timestamp = datetime.utcnow()

        device = self.topology.get_device(hostname)
        if device:
            self.topology.set_device_status(hostname, "up")

        return SimulatedEvent(
            event_id=self._next_event_id(),
            timestamp=timestamp,
            device_id=self._get_device_id(hostname),
            device_hostname=hostname,
            event_type="device_recovery",
            interface_id=None,
            severity=AlarmSeverity.INFORMATIONAL.value,
            message=f"Device {hostname} has recovered - responding to SNMP polls",
        )

    # ============================================================================
    # Network Quality Events
    # ============================================================================

    def high_latency(
        self,
        hostname: str,
        interface_name: str,
        latency_ms: int = 150,
        timestamp: Optional[datetime] = None,
    ) -> SimulatedEvent:
        """Generate high latency event."""
        if not timestamp:
            timestamp = datetime.utcnow()

        severity = (
            AlarmSeverity.CRITICAL.value
            if latency_ms > 500
            else AlarmSeverity.MAJOR.value
            if latency_ms > 200
            else AlarmSeverity.MINOR.value
        )

        return SimulatedEvent(
            event_id=self._next_event_id(),
            timestamp=timestamp,
            device_id=self._get_device_id(hostname),
            device_hostname=hostname,
            event_type="high_latency",
            interface_id=interface_name,
            severity=severity,
            message=f"High latency detected on {interface_name}: {latency_ms}ms (threshold: 100ms)",
        )

    def packet_loss(
        self,
        hostname: str,
        interface_name: str,
        loss_percent: float = 5.0,
        timestamp: Optional[datetime] = None,
    ) -> SimulatedEvent:
        """Generate packet loss event."""
        if not timestamp:
            timestamp = datetime.utcnow()

        severity = (
            AlarmSeverity.CRITICAL.value
            if loss_percent > 10
            else AlarmSeverity.MAJOR.value
            if loss_percent > 5
            else AlarmSeverity.MINOR.value
        )

        return SimulatedEvent(
            event_id=self._next_event_id(),
            timestamp=timestamp,
            device_id=self._get_device_id(hostname),
            device_hostname=hostname,
            event_type="packet_loss",
            interface_id=interface_name,
            severity=severity,
            message=f"Packet loss detected on {interface_name}: {loss_percent:.2f}% (threshold: 1%)",
        )

    # ============================================================================
    # Link Events
    # ============================================================================

    def link_flapping(
        self,
        source_device: str,
        source_iface: str,
        target_device: str,
        target_iface: str,
        flap_count: int = 5,
        timestamp: Optional[datetime] = None,
    ) -> List[SimulatedEvent]:
        """Generate a series of up/down events (link flapping)."""
        events = []
        if not timestamp:
            timestamp = datetime.utcnow()

        for i in range(flap_count):
            event_time = timestamp + timedelta(seconds=i * 2)
            status = "down" if i % 2 == 0 else "up"

            # Source side event
            events.append(
                SimulatedEvent(
                    event_id=self._next_event_id(),
                    timestamp=event_time,
                    device_id=self._get_device_id(source_device),
                    device_hostname=source_device,
                    event_type="link_down" if status == "down" else "link_up",
                    interface_id=source_iface,
                    severity=AlarmSeverity.MINOR.value,
                    message=f"Link {source_iface} on {source_device} is {status.upper()}",
                )
            )

            # Target side event
            events.append(
                SimulatedEvent(
                    event_id=self._next_event_id(),
                    timestamp=event_time + timedelta(milliseconds=100),
                    device_id=self._get_device_id(target_device),
                    device_hostname=target_device,
                    event_type="link_down" if status == "down" else "link_up",
                    interface_id=target_iface,
                    severity=AlarmSeverity.MINOR.value,
                    message=f"Link {target_iface} on {target_device} is {status.upper()}",
                )
            )

        return events

    # ============================================================================
    # Cascade Events
    # ============================================================================

    def generate_cascade_events(
        self,
        root_device: str,
        root_interface: Optional[str],
        event_type: str,
        timestamp: Optional[datetime] = None,
    ) -> List[SimulatedEvent]:
        """Generate cascading events following topology."""
        if not timestamp:
            timestamp = datetime.utcnow()

        events = []

        # Root cause event
        if event_type == "interface_down" and root_interface:
            events.append(
                self.interface_down(root_device, root_interface, timestamp)
            )
        elif event_type == "device_unreachable":
            events.append(self.device_unreachable(root_device, timestamp))

        # Get affected devices
        affected_devices = self.topology.get_downstream_devices(root_device)

        # Generate secondary alarms for downstream devices
        for i, affected_device in enumerate(affected_devices):
            delay = timedelta(seconds=2 + i)

            if event_type == "interface_down":
                # Device can't reach upstream
                events.append(
                    self.device_unreachable(affected_device, timestamp + delay)
                )
            elif event_type == "device_unreachable":
                # Affected devices also go unreachable
                events.append(
                    self.device_unreachable(affected_device, timestamp + delay)
                )

        return events

    def generate_recovery_cascade(
        self,
        root_device: str,
        root_interface: Optional[str],
        timestamp: Optional[datetime] = None,
    ) -> List[SimulatedEvent]:
        """Generate recovery events following a failure."""
        if not timestamp:
            timestamp = datetime.utcnow()

        events = []

        # Root recovery
        if root_interface:
            events.append(self.interface_up(root_device, root_interface, timestamp))
        else:
            events.append(self.device_recovery(root_device, timestamp))

        # Downstream recoveries
        affected_devices = self.topology.get_downstream_devices(root_device)
        for i, affected_device in enumerate(affected_devices):
            delay = timedelta(seconds=1 + i)
            events.append(
                self.device_recovery(affected_device, timestamp + delay)
            )

        return events
