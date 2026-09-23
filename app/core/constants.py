"""Application constants and enums."""

from enum import Enum


class AlarmSeverity(str, Enum):
    """Alarm severity levels following RFC 3164."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    WARNING = "warning"
    INFORMATIONAL = "informational"
    DEBUG = "debug"


class AlarmType(str, Enum):
    """Types of network alarms."""
    INTERFACE_DOWN = "interface_down"
    INTERFACE_DEGRADED = "interface_degraded"
    DEVICE_UNREACHABLE = "device_unreachable"
    HIGH_LATENCY = "high_latency"
    PACKET_LOSS = "packet_loss"
    LINK_FLAPPING = "link_flapping"
    DEVICE_RECOVERY = "device_recovery"
    INTERFACE_RECOVERY = "interface_recovery"
    DEPENDENCY_FAILURE = "dependency_failure"


class AlarmStatus(str, Enum):
    """Alarm operational status."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    SUPPRESSED = "suppressed"
    RESOLVED = "resolved"
    CLEARED = "cleared"


class IncidentState(str, Enum):
    """Incident lifecycle states."""
    OPEN = "open"
    CORRELATED = "correlated"
    ROOT_CAUSE_IDENTIFIED = "root_cause_identified"
    ACTIVE = "active"
    RECOVERING = "recovering"
    RESOLVED = "resolved"


class DeviceType(str, Enum):
    """Network device types."""
    CORE_ROUTER = "core_router"
    DISTRIBUTION_ROUTER = "distribution_router"
    ACCESS_SWITCH = "access_switch"
    EDGE_ROUTER = "edge_router"
    AGGREGATION_SWITCH = "aggregation_switch"
    HOST = "host"
    FIREWALL = "firewall"
    LOAD_BALANCER = "load_balancer"


class InterfaceType(str, Enum):
    """Network interface types."""
    GIGABIT_ETHERNET = "gigabit_ethernet"
    TEN_GIGABIT_ETHERNET = "ten_gigabit_ethernet"
    SERIAL = "serial"
    VIRTUAL = "virtual"
    LOOPBACK = "loopback"


# Severity scoring
SEVERITY_SCORES = {
    AlarmSeverity.CRITICAL: 100,
    AlarmSeverity.MAJOR: 80,
    AlarmSeverity.MINOR: 60,
    AlarmSeverity.WARNING: 40,
    AlarmSeverity.INFORMATIONAL: 20,
    AlarmSeverity.DEBUG: 10,
}

# RCA confidence thresholds
RCA_CONFIDENCE_THRESHOLD = 0.65
CORRELATION_SCORE_THRESHOLD = 0.5

# Suppression rules
MAX_SUPPRESSED_ALARMS_PER_INCIDENT = 1000
ALARM_DEDUP_WINDOW_SECONDS = 300

# Timeouts
DEVICE_UNREACHABLE_THRESHOLD_SECONDS = 90
LINK_FLAP_THRESHOLD_COUNT = 5
LINK_FLAP_TIME_WINDOW_SECONDS = 600
