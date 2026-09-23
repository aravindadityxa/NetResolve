# Network Simulator Guide

## Overview

The NetResolve simulator generates realistic network events without requiring physical hardware. It simulates a hierarchical network topology with core, distribution, and access layers.

## Simulated Topology

```
                      CORE-R1
                     (10.0.0.1)
                    /          \
              DIST-R1        DIST-R2
            (10.0.1.1)      (10.0.2.1)
              /    \          /    \
          ACC-1  ACC-2     ACC-3  ACC-4
        (10.1.x.1)        (10.1.x.1)
```

### Devices

**Core Layer:**
- CORE-R1: Primary backbone router
  - Interfaces: GigabitEthernet0/1, GigabitEthernet0/2, Loopback0

**Distribution Layer:**
- DIST-R1: Regional aggregation router
  - Upstream: CORE-R1
  - Downstream: ACCESS-SW1, ACCESS-SW2
- DIST-R2: Regional aggregation router
  - Upstream: CORE-R1
  - Downstream: ACCESS-SW3, ACCESS-SW4

**Access Layer:**
- ACCESS-SW1 through ACCESS-SW4: End-user access switches
  - Upstream: DIST-R1 or DIST-R2

### Links

Total 6 physical links:
- CORE-R1 → DIST-R1
- CORE-R1 → DIST-R2
- DIST-R1 → ACCESS-SW1
- DIST-R1 → ACCESS-SW2
- DIST-R2 → ACCESS-SW3
- DIST-R2 → ACCESS-SW4

## Available Scenarios

### 1. Core Interface Failure

**Name:** `core_interface_failure`

**What Happens:**
- CORE-R1 GigabitEthernet0/1 goes DOWN
- Downstream cascade: DIST-R1 detects unreachable
- Further cascade: ACCESS-SW1, ACCESS-SW2 unreachable

**Generated Alarms:**
- 1 Interface DOWN (root cause)
- 3 Device UNREACHABLE (secondary)
- Total: 4 alarms

**Expected RCA Result:**
- Root Cause: CORE-R1 GigabitEthernet0/1 DOWN
- Confidence: ~94%
- Affected: DIST-R1, ACCESS-SW1, ACCESS-SW2 (3 devices)
- Suppressed: 3 alarms

**Timeline:**
```
T+0s: CORE-R1 interface down
T+2s: DIST-R1 unreachable (detected)
T+3s: ACCESS-SW1 unreachable (detected)
T+4s: ACCESS-SW2 unreachable (detected)
```

### 2. Core Interface Recovery

**Name:** `core_interface_recovery`

**What Happens:**
- CORE-R1 GigabitEthernet0/1 comes UP
- Downstream devices recover in order

**Generated Alarms:**
- 5 Recovery events (1 interface + 4 devices)

**Expected Result:**
- Previous incident transitions to RESOLVED
- Recovery events show fault isolation working

### 3. Distribution Router Failure

**Name:** `distribution_failure`

**What Happens:**
- DIST-R1 becomes UNREACHABLE (complete device failure)
- Downstream devices detect unreachable: ACCESS-SW1, ACCESS-SW2

**Generated Alarms:**
- 1 Device UNREACHABLE (root cause)
- 2 Device UNREACHABLE (secondary)
- Total: 3 alarms

**Expected RCA Result:**
- Root Cause: DIST-R1 UNREACHABLE
- Confidence: ~90%
- Affected: ACCESS-SW1, ACCESS-SW2 (2 devices)
- Suppressed: 2 alarms

### 4. Distribution Router Recovery

**Name:** `distribution_recovery`

**What Happens:**
- DIST-R1 recovers
- Downstream devices recover

**Expected Result:**
- Incident resolves, shows MTTR

### 5. Access Switch Failure

**Name:** `access_failure`

**What Happens:**
- ACCESS-SW1 becomes UNREACHABLE

**Generated Alarms:**
- 1 Device UNREACHABLE (root cause only, no downstream)

**Expected RCA Result:**
- Root Cause: ACCESS-SW1 UNREACHABLE
- Confidence: ~95%
- No affected devices (leaf device)
- No suppressed alarms

### 6. Access Switch Recovery

**Name:** `access_recovery`

**What Happens:**
- ACCESS-SW1 recovers

### 7. Link Flapping

**Name:** `link_flapping`

**What Happens:**
- Link between DIST-R1 and ACCESS-SW1 goes DOWN/UP 5 times
- Rapid up/down cycles simulate unstable connection

**Generated Events:**
```
T+0s: DIST-R1 Gi0/2 DOWN
T+0.1s: ACCESS-SW1 Gi0/1 DOWN
T+2s: DIST-R1 Gi0/2 UP
T+2.1s: ACCESS-SW1 Gi0/1 UP
T+4s: DIST-R1 Gi0/2 DOWN
... (repeats)
```

**Expected Alarm:**
- Link flapping detected after 5+ events in 10-minute window

### 8. High Latency

**Name:** `high_latency`

**What Happens:**
- DIST-R1 GigabitEthernet0/2 experiences 250ms latency (threshold: 100ms)

**Generated Alarm:**
- 1 HIGH_LATENCY alarm on DIST-R1

### 9. Packet Loss

**Name:** `packet_loss`

**What Happens:**
- ACCESS-SW3 GigabitEthernet0/1 experiences 8.5% packet loss (threshold: 1%)

**Generated Alarm:**
- 1 PACKET_LOSS alarm on ACCESS-SW3

### 10. Cascading Dual Failure

**Name:** `dual_failure`

**What Happens:**
- CORE-R1 GigabitEthernet0/1 fails → affects DIST-R1, ACCESS-SW1, ACCESS-SW2
- 3 seconds later: CORE-R1 GigabitEthernet0/2 fails → affects DIST-R2, ACCESS-SW3, ACCESS-SW4

**Generated Alarms:**
- 8 total (2 root causes + 6 secondary)

**Expected RCA:**
- May create 2 separate incidents or 1 with multiple root causes
- Demonstrates capability to handle complex cascades

### 11. Network Recovery

**Name:** `network_recovery`

**What Happens:**
- All failed links recover in cascade order
- Core recovers first, then distribution, then access

**Demonstrates:**
- MTTR calculation
- Recovery cascade detection
- Multiple incident resolution

## Using the Simulator

### Via REST API

```bash
# Get simulator status
curl http://localhost:8000/api/simulator/status

# List available scenarios
curl http://localhost:8000/api/simulator/scenarios

# Run a scenario
curl -X POST http://localhost:8000/api/simulator/scenarios/core_interface_failure

# Get event history
curl http://localhost:8000/api/simulator/history
```

### Programmatically

```python
from app.simulator import get_simulator

# Get simulator
sim = get_simulator()

# Get topology
topology = sim.get_topology_status()
print(f"Network has {len(topology['devices'])} devices")

# Run scenario
result = sim.run_scenario('core_interface_failure')
print(f"Generated {result['events_generated']} events")
for event in result['events']:
    print(f"  - {event['device_hostname']}: {event['message']}")

# Get history
history = sim.get_event_history(limit=20)
for event in history:
    print(f"{event['timestamp']} {event['device_hostname']} {event['event_type']}")
```

## Event Types

### Network Layer Events

| Event Type | Severity | Typical Cause | Secondary Effects |
|-----------|----------|---------------|-------------------|
| `interface_down` | MAJOR | Cable disconnect, port shutdown | Downstream unreachable |
| `device_unreachable` | CRITICAL | Device crash/power loss | Cascading failures |
| `link_flapping` | MINOR | Unstable connection | Packet loss, latency |

### Quality Events

| Event Type | Severity | Typical Cause |
|-----------|----------|----------------|
| `high_latency` | MINOR/MAJOR | Congestion, distance |
| `packet_loss` | MINOR/MAJOR | Congestion, errors |

### Recovery Events

| Event Type | Severity | Typical Cause |
|-----------|----------|----------------|
| `interface_recovery` | INFORMATIONAL | Admin restore, auto-healing |
| `device_recovery` | INFORMATIONAL | Device reboot, power restore |

## Example Workflow

```
1. Start NetResolve services
   docker-compose up -d

2. Open browser to dashboard
   http://localhost:3000

3. Trigger scenario
   POST /api/simulator/scenarios/core_interface_failure

4. Observe on dashboard:
   - Alarms appear (interface down)
   - RCA runs (topology analysis)
   - Incident created with blast radius
   - Secondary alarms suppressed
   - Topology view shows affected devices

5. Fix the issue (run recovery scenario)
   POST /api/simulator/scenarios/core_interface_recovery

6. Observe on dashboard:
   - Recovery events appear
   - Incident transitions to RECOVERED
   - Metrics update (MTTR calculated)
```

## Creating Custom Scenarios

### Simple Event Scenario

```python
from app.simulator import get_simulator
from datetime import datetime, timedelta

sim = get_simulator()
gen = sim.event_generator

# Generate a single interface down event
start_time = datetime.utcnow()
event = gen.interface_down("DIST-R1", "GigabitEthernet0/2", start_time)

# Custom events can be added to history for collection
sim.event_history.append(event)
```

### Complex Cascade Scenario

```python
# Generate cascading failure scenario
events = gen.generate_cascade_events(
    root_device="DIST-R1",
    root_interface=None,
    event_type="device_unreachable",
    timestamp=datetime.utcnow()
)

for event in events:
    sim.event_history.append(event)
```

## Simulation Limitations

The simulator is designed for demonstration and local testing:

- **No real SNMP/Syslog**: Events are synthetic, not from actual devices
- **Simplified Topology**: 7 devices; production networks have thousands
- **Instant Propagation**: Real cascades can take seconds to minutes
- **No State Persistence**: Events are in-memory; restart clears history
- **Synchronous Events**: Real networks have asynchronous failures

For production monitoring, integrate real SNMP traps and syslog streams.

## Next Steps

1. Run a scenario to generate events
2. Watch the correlation engine group alarms
3. See RCA identify root cause
4. Observe suppression hide secondary alarms
5. Check incident lifecycle through resolution
6. Export metrics and view in Grafana
