"""Network simulator service."""

from typing import List, Optional, Dict
from datetime import datetime
import threading
import time

from app.core.logging import logger
from app.simulator.topology import SimulatedTopology
from app.simulator.events import SimulatedEvent, EventGenerator
from app.simulator.scenarios import ScenarioRunner


class NetworkSimulator:
    """Manages simulated network and event generation."""

    def __init__(self):
        """Initialize simulator."""
        self.topology = SimulatedTopology()
        self.event_generator = EventGenerator(self.topology)
        self.scenario_runner = ScenarioRunner(self.topology)
        self.event_history: List[SimulatedEvent] = []
        self.is_running = False
        self.current_scenario = None
        self._lock = threading.Lock()

    def get_topology(self) -> SimulatedTopology:
        """Get the simulated topology."""
        return self.topology

    def get_topology_status(self) -> Dict:
        """Get current topology status."""
        devices = []
        for device in self.topology.get_all_devices():
            devices.append({
                "hostname": device.hostname,
                "ip": device.ip_address,
                "role": device.role.value,
                "status": device.status,
                "interfaces": {
                    name: {
                        "name": iface.name,
                        "status": iface.status,
                        "ip": iface.ip_address,
                    }
                    for name, iface in device.interfaces.items()
                },
            })

        links = []
        for link in self.topology.get_all_links():
            links.append({
                "source_device": link.source_device,
                "source_interface": link.source_interface,
                "target_device": link.target_device,
                "target_interface": link.target_interface,
                "status": link.status,
            })

        return {"devices": devices, "links": links}

    def run_scenario(self, scenario_name: str) -> Dict:
        """
        Run a predefined scenario and generate events.

        Returns dict with scenario metadata and generated events.
        """
        scenarios = self.scenario_runner.get_all_scenarios()

        if scenario_name not in scenarios:
            raise ValueError(f"Unknown scenario: {scenario_name}")

        scenario_info = scenarios[scenario_name]
        logger.info(f"Running scenario: {scenario_info['name']}")

        with self._lock:
            self.current_scenario = scenario_name

        # Generate events
        scenario_method = scenario_info["method"]
        events = scenario_method()

        with self._lock:
            self.event_history.extend(events)

        return {
            "scenario": scenario_name,
            "name": scenario_info["name"],
            "description": scenario_info["description"],
            "events_generated": len(events),
            "expected_alarms": scenario_info.get("expected_alarms", 0),
            "expected_root_cause": scenario_info.get("expected_root_cause"),
            "events": [self._event_to_dict(e) for e in events],
        }

    def generate_random_event(self) -> Optional[SimulatedEvent]:
        """Generate a random event."""
        import random

        devices = list(self.topology.devices.values())
        if not devices:
            return None

        device = random.choice(devices)
        event_type = random.choice(["interface_down", "high_latency", "packet_loss"])

        try:
            if event_type == "interface_down":
                interfaces = list(device.interfaces.keys())
                if interfaces:
                    interface = random.choice(interfaces)
                    event = self.event_generator.interface_down(
                        device.hostname, interface
                    )
            elif event_type == "high_latency":
                interfaces = list(device.interfaces.keys())
                if interfaces:
                    interface = random.choice(interfaces)
                    event = self.event_generator.high_latency(
                        device.hostname, interface, latency_ms=random.randint(150, 500)
                    )
            else:  # packet_loss
                interfaces = list(device.interfaces.keys())
                if interfaces:
                    interface = random.choice(interfaces)
                    event = self.event_generator.packet_loss(
                        device.hostname, interface, loss_percent=random.uniform(1, 10)
                    )

            with self._lock:
                self.event_history.append(event)

            return event
        except Exception as e:
            logger.error(f"Error generating random event: {e}")
            return None

    def get_event_history(self, limit: int = 100) -> List[Dict]:
        """Get event history."""
        with self._lock:
            events = self.event_history[-limit:]

        return [self._event_to_dict(e) for e in events]

    def get_event_count(self) -> int:
        """Get total event count."""
        with self._lock:
            return len(self.event_history)

    def clear_history(self):
        """Clear event history."""
        with self._lock:
            self.event_history.clear()

        # Reset topology to initial state
        self.topology = SimulatedTopology()
        self.event_generator = EventGenerator(self.topology)
        self.scenario_runner = ScenarioRunner(self.topology)
        logger.info("Simulator history cleared and topology reset")

    def get_scenarios(self) -> Dict:
        """Get all available scenarios."""
        scenarios = self.scenario_runner.get_all_scenarios()
        return {
            name: {
                "name": info["name"],
                "description": info["description"],
                "expected_alarms": info.get("expected_alarms", 0),
                "expected_root_cause": info.get("expected_root_cause"),
            }
            for name, info in scenarios.items()
        }

    @staticmethod
    def _event_to_dict(event: SimulatedEvent) -> Dict:
        """Convert event to dictionary."""
        return {
            "event_id": event.event_id,
            "timestamp": event.timestamp.isoformat(),
            "device_id": event.device_id,
            "device_hostname": event.device_hostname,
            "event_type": event.event_type,
            "interface_id": event.interface_id,
            "severity": event.severity,
            "message": event.message,
            "source": event.source,
        }


# Global simulator instance
_simulator = None


def get_simulator() -> NetworkSimulator:
    """Get or create global simulator instance."""
    global _simulator
    if _simulator is None:
        _simulator = NetworkSimulator()
        logger.info("Network simulator initialized")
    return _simulator
