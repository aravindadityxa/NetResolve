"""Predefined failure scenarios for demonstration."""

from datetime import datetime, timedelta
from typing import List

from app.simulator.events import SimulatedEvent, EventGenerator
from app.simulator.topology import SimulatedTopology


class ScenarioRunner:
    """Runs predefined scenarios to generate events."""

    def __init__(self, topology: SimulatedTopology):
        """Initialize scenario runner."""
        self.topology = topology
        self.event_generator = EventGenerator(topology)

    def scenario_core_interface_failure(
        self,
        start_time: datetime = None,
    ) -> List[SimulatedEvent]:
        """
        Scenario: Core Router Interface Failure

        CORE-R1 GigabitEthernet0/1 goes down.
        Expected: 4 alarms (1 root cause + 3 secondary)
        - Root cause: CORE-R1 interface down
        - Secondary: DIST-R1, ACCESS-SW1, ACCESS-SW2 unreachable
        """
        if not start_time:
            start_time = datetime.utcnow()

        events = self.event_generator.generate_cascade_events(
            root_device="CORE-R1",
            root_interface="GigabitEthernet0/1",
            event_type="interface_down",
            timestamp=start_time,
        )

        return events

    def scenario_core_interface_recovery(
        self,
        start_time: datetime = None,
    ) -> List[SimulatedEvent]:
        """
        Scenario: Core Router Interface Recovery

        CORE-R1 GigabitEthernet0/1 comes back up.
        Expected: Incident transitions to RESOLVED
        """
        if not start_time:
            start_time = datetime.utcnow()

        events = self.event_generator.generate_recovery_cascade(
            root_device="CORE-R1",
            root_interface="GigabitEthernet0/1",
            timestamp=start_time,
        )

        return events

    def scenario_distribution_router_failure(
        self,
        start_time: datetime = None,
    ) -> List[SimulatedEvent]:
        """
        Scenario: Distribution Router Failure

        DIST-R1 becomes unreachable (complete device failure).
        Expected: 3 alarms (1 root cause + 2 secondary)
        - Root cause: DIST-R1 unreachable
        - Secondary: ACCESS-SW1, ACCESS-SW2 unreachable
        """
        if not start_time:
            start_time = datetime.utcnow()

        events = self.event_generator.generate_cascade_events(
            root_device="DIST-R1",
            root_interface=None,
            event_type="device_unreachable",
            timestamp=start_time,
        )

        return events

    def scenario_distribution_router_recovery(
        self,
        start_time: datetime = None,
    ) -> List[SimulatedEvent]:
        """
        Scenario: Distribution Router Recovery

        DIST-R1 comes back online.
        Expected: Incident transitions to RESOLVED
        """
        if not start_time:
            start_time = datetime.utcnow()

        events = self.event_generator.generate_recovery_cascade(
            root_device="DIST-R1",
            root_interface=None,
            timestamp=start_time,
        )

        return events

    def scenario_access_switch_failure(
        self,
        start_time: datetime = None,
    ) -> List[SimulatedEvent]:
        """
        Scenario: Access Switch Failure

        ACCESS-SW1 becomes unreachable.
        Expected: 1 alarm (single device failure, no downstream)
        """
        if not start_time:
            start_time = datetime.utcnow()

        events = self.event_generator.generate_cascade_events(
            root_device="ACCESS-SW1",
            root_interface=None,
            event_type="device_unreachable",
            timestamp=start_time,
        )

        return events

    def scenario_access_switch_recovery(
        self,
        start_time: datetime = None,
    ) -> List[SimulatedEvent]:
        """
        Scenario: Access Switch Recovery

        ACCESS-SW1 comes back online.
        """
        if not start_time:
            start_time = datetime.utcnow()

        events = self.event_generator.generate_recovery_cascade(
            root_device="ACCESS-SW1",
            root_interface=None,
            timestamp=start_time,
        )

        return events

    def scenario_link_flapping(
        self,
        start_time: datetime = None,
    ) -> List[SimulatedEvent]:
        """
        Scenario: Link Flapping

        Link between DIST-R1 and ACCESS-SW1 flaps 5 times.
        Expected: Alarm for link flapping detected
        """
        if not start_time:
            start_time = datetime.utcnow()

        events = self.event_generator.link_flapping(
            source_device="DIST-R1",
            source_iface="GigabitEthernet0/2",
            target_device="ACCESS-SW1",
            target_iface="GigabitEthernet0/1",
            flap_count=5,
            timestamp=start_time,
        )

        return events

    def scenario_high_latency(
        self,
        start_time: datetime = None,
    ) -> List[SimulatedEvent]:
        """
        Scenario: High Latency Detection

        DIST-R1 GigabitEthernet0/2 experiences high latency.
        """
        if not start_time:
            start_time = datetime.utcnow()

        events = [
            self.event_generator.high_latency(
                hostname="DIST-R1",
                interface_name="GigabitEthernet0/2",
                latency_ms=250,
                timestamp=start_time,
            )
        ]

        return events

    def scenario_packet_loss(
        self,
        start_time: datetime = None,
    ) -> List[SimulatedEvent]:
        """
        Scenario: Packet Loss Detection

        ACCESS-SW3 GigabitEthernet0/1 experiences packet loss.
        """
        if not start_time:
            start_time = datetime.utcnow()

        events = [
            self.event_generator.packet_loss(
                hostname="ACCESS-SW3",
                interface_name="GigabitEthernet0/1",
                loss_percent=8.5,
                timestamp=start_time,
            )
        ]

        return events

    def scenario_cascading_dual_failure(
        self,
        start_time: datetime = None,
    ) -> List[SimulatedEvent]:
        """
        Scenario: Cascading Dual Failure

        Both DIST-R1 and DIST-R2 interfaces to CORE fail.
        This tests correlation of multiple independent failures.
        Expected: Two incidents (or one with two root causes detected)
        """
        if not start_time:
            start_time = datetime.utcnow()

        events = []

        # First failure: DIST-R1 interface
        events.extend(
            self.event_generator.generate_cascade_events(
                root_device="CORE-R1",
                root_interface="GigabitEthernet0/1",
                event_type="interface_down",
                timestamp=start_time,
            )
        )

        # Second failure: DIST-R2 interface (3 seconds later)
        events.extend(
            self.event_generator.generate_cascade_events(
                root_device="CORE-R1",
                root_interface="GigabitEthernet0/2",
                event_type="interface_down",
                timestamp=start_time + timedelta(seconds=3),
            )
        )

        return events

    def scenario_network_recovery(
        self,
        start_time: datetime = None,
    ) -> List[SimulatedEvent]:
        """
        Scenario: Network Wide Recovery

        After all devices fail, they recover.
        Tests MTTR and recovery cascade.
        """
        if not start_time:
            start_time = datetime.utcnow()

        events = []

        # Recovery in order: Core first, then distribution, then access
        events.extend(
            self.event_generator.generate_recovery_cascade(
                root_device="CORE-R1",
                root_interface="GigabitEthernet0/1",
                timestamp=start_time,
            )
        )

        events.extend(
            self.event_generator.generate_recovery_cascade(
                root_device="CORE-R1",
                root_interface="GigabitEthernet0/2",
                timestamp=start_time + timedelta(seconds=5),
            )
        )

        return events

    def get_all_scenarios(self) -> dict:
        """Get all available scenarios."""
        return {
            "core_interface_failure": {
                "name": "Core Router Interface Failure",
                "description": "Interface down on CORE-R1, affecting distribution layer",
                "expected_alarms": 4,
                "expected_root_cause": "CORE-R1 GigabitEthernet0/1",
                "method": self.scenario_core_interface_failure,
            },
            "core_interface_recovery": {
                "name": "Core Interface Recovery",
                "description": "Recovery of failed core interface",
                "expected_alarms": 4,
                "method": self.scenario_core_interface_recovery,
            },
            "distribution_failure": {
                "name": "Distribution Router Failure",
                "description": "Complete distribution router failure",
                "expected_alarms": 3,
                "expected_root_cause": "DIST-R1",
                "method": self.scenario_distribution_router_failure,
            },
            "distribution_recovery": {
                "name": "Distribution Router Recovery",
                "description": "Recovery of failed distribution router",
                "expected_alarms": 3,
                "method": self.scenario_distribution_router_recovery,
            },
            "access_failure": {
                "name": "Access Switch Failure",
                "description": "Single access switch failure",
                "expected_alarms": 1,
                "expected_root_cause": "ACCESS-SW1",
                "method": self.scenario_access_switch_failure,
            },
            "access_recovery": {
                "name": "Access Switch Recovery",
                "description": "Recovery of failed access switch",
                "expected_alarms": 1,
                "method": self.scenario_access_switch_recovery,
            },
            "link_flapping": {
                "name": "Link Flapping",
                "description": "Link interface flapping (up/down)",
                "expected_alarms": 10,  # 5 flaps * 2 sides
                "method": self.scenario_link_flapping,
            },
            "high_latency": {
                "name": "High Latency",
                "description": "Latency spike on interface",
                "expected_alarms": 1,
                "method": self.scenario_high_latency,
            },
            "packet_loss": {
                "name": "Packet Loss",
                "description": "Packet loss on interface",
                "expected_alarms": 1,
                "method": self.scenario_packet_loss,
            },
            "dual_failure": {
                "name": "Cascading Dual Failure",
                "description": "Two core interfaces fail simultaneously",
                "expected_alarms": 8,  # 2 root causes + 6 secondary
                "method": self.scenario_cascading_dual_failure,
            },
            "network_recovery": {
                "name": "Network Wide Recovery",
                "description": "Recovery of cascading failures",
                "expected_alarms": 8,  # Recovery events
                "method": self.scenario_network_recovery,
            },
        }
