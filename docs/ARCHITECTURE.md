# NetResolve Architecture

## Overview

NetResolve is an automated network root cause analysis and alarm suppression platform. It processes network events through a multi-stage pipeline to identify root causes, correlate related alarms, and suppress secondary alarms.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Network Simulator                         │
│  (Topology, Devices, Interfaces, Event Generation)          │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   Event Collector                           │
│  (SNMP, Syslog, Simulator, etc.)                           │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Apache Kafka Event Bus                         │
│  (Topics: events, alarms)                                   │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│           Event Normalization Service                       │
│  (Parse, Enrich, Create Alarm Objects)                      │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│        Alarm Correlation Engine                             │
│  (Group related alarms, calculate correlation scores)       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│    Topology-Aware RCA Engine                                │
│  (Analyze topology, identify root cause, calc blast radius) │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│         Alarm Suppression Engine                            │
│  (Suppress secondary alarms, keep root cause visible)       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│       Incident Manager                                      │
│  (Create/update/resolve incidents, track lifecycle)         │
└───────────────────────┬─────────────────────────────────────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
     PostgreSQL   FastAPI REST   Metrics
     (Database)    (API Layer)  (Prometheus)
          │             │             │
          └─────────────┼─────────────┘
                        ▼
        ┌───────────────────────────────┐
        │    Web Dashboard (React)       │
        │  (Incident view, Topology,    │
        │   Simulator, Analytics)       │
        └───────────────────────────────┘
```

## Core Components

### 1. Network Simulator (`app/simulator/`)

**Purpose:** Generate realistic network events without physical hardware.

**Features:**
- Simulates network topology (routers, switches, interfaces, links)
- Generates events: interface down, device unreachable, link flapping, recovery
- Supports pre-built scenarios for demonstration
- Can be controlled via REST API

**Key Files:**
- `topology.py` - Simulated topology definition
- `device.py` - Simulated device logic
- `events.py` - Event generation
- `scenarios.py` - Predefined failure scenarios

### 2. Event Collector (`app/messaging/collector.py`)

**Purpose:** Ingest events from various sources.

**Sources:**
- Network simulator
- SNMP traps
- Syslog messages
- Custom collectors

**Output:** Events published to Kafka

### 3. Kafka Event Bus (`app/messaging/kafka.py`)

**Purpose:** High-throughput event streaming.

**Topics:**
- `netresolve.events` - Raw network events
- `netresolve.alarms` - Normalized alarms

**Design:** Decouples components for scalability.

### 4. Alarm Normalization (`app/messaging/normalizer.py`)

**Purpose:** Convert raw events to normalized alarm objects.

**Process:**
1. Parse raw event data
2. Extract key fields (device, interface, type, severity)
3. Create correlation IDs
4. Enrich with topology/device info
5. Publish to alarms topic

### 5. Alarm Correlation Engine (`app/correlation/`)

**Purpose:** Group related alarms into correlated sets.

**Algorithm:**
```
For each alarm:
  1. Calculate correlation score against existing groups
  2. Score = temporal_score + topology_score + dependency_score
  3. If score > threshold: add to group
  4. Else: create new group
```

**Factors:**
- **Temporal:** Alarms within same time window
- **Topological:** Alarms on connected devices
- **Dependency:** Device relationships
- **Severity:** Higher severity weighted more
- **Type:** Same alarm types correlate better

**Output:** Correlated alarm groups with scores.

### 6. Topology-Aware RCA Engine (`app/rca/`)

**Purpose:** Identify probable root cause for each correlated group.

**Algorithm:**
```
1. Build current topology graph
2. For each correlated alarm group:
   a. Find earliest alarm (likely root cause)
   b. Calculate blast radius (downstream devices)
   c. Check if all affected devices are downstream
   d. Calculate confidence score
   e. Generate reasoning
```

**Root Cause Identification:**
- **First Event Principle:** Earliest alarm is likely root cause
- **Topology Validation:** Root cause must be upstream of affected
- **Cascade Pattern:** Secondary alarms follow causality
- **Recovery Signal:** Device recovery confirms root cause

**Confidence Scoring:**
```
confidence = (
    temporal_factor (0-1) +
    topology_factor (0-1) +
    cascade_factor (0-1) +
    recovery_factor (0-1)
) / 4
```

**Output:** RCA results with confidence, reasoning, affected devices.

### 7. Alarm Suppression Engine (`app/suppression/`)

**Purpose:** Suppress secondary alarms to reduce noise.

**Algorithm:**
```
1. Get RCA results
2. For each alarm in group:
   a. If not root cause AND in blast radius: suppress
   b. Store suppression reason
3. Keep only root cause visible
```

**Suppression Reasons:**
- "Secondary alarm: downstream of identified root cause"
- "Dependent failure: caused by upstream device"
- "Expected recovery cascade"

**Output:** Suppressed alarms marked with reason.

### 8. Incident Manager (`app/services/incident_service.py`)

**Purpose:** Create and manage incidents through lifecycle.

**Incident States:**
```
OPEN → CORRELATED → ROOT_CAUSE_IDENTIFIED → ACTIVE → RECOVERING → RESOLVED
```

**Lifecycle:**
1. **OPEN:** Initial incident created from alarm
2. **CORRELATED:** Related alarms grouped
3. **ROOT_CAUSE_IDENTIFIED:** RCA completed
4. **ACTIVE:** Incident is being investigated
5. **RECOVERING:** Recovery signals detected
6. **RESOLVED:** Incident closed

**Metrics:**
- MTTD (Mean Time to Detect): Creation to first correlation
- MTTI (Mean Time to Identify): Creation to root cause identified
- MTTR (Mean Time to Resolve): Creation to resolved

### 9. FastAPI REST API (`app/api/`)

**Purpose:** Provide HTTP interface for dashboards and external systems.

**Key Endpoints:**
- `GET /api/health` - Health check
- `GET /api/devices` - List devices
- `GET /api/topology` - Get network topology
- `GET /api/alarms` - List alarms
- `GET /api/incidents` - List incidents
- `GET /api/incidents/{id}` - Get incident details
- `POST /api/simulator/scenarios/{name}` - Run simulator scenario
- `GET /api/metrics` - Prometheus metrics

**Features:**
- Request validation (Pydantic)
- Response schemas
- Error handling
- API documentation (Swagger/OpenAPI)

### 10. Database Layer (`app/models/`)

**Technology:** SQLAlchemy ORM + PostgreSQL

**Key Tables:**
- `devices` - Network devices
- `interfaces` - Device interfaces
- `links` - Interface connections
- `network_events` - Raw events
- `alarms` - Normalized alarms
- `incidents` - Incidents
- `incident_alarms` - Incident-alarm mappings
- `timeline_events` - Incident timeline

**Indexes:**
- Fast queries on timestamp, device_id, correlation_id, status, severity

### 11. Web Dashboard

**Technology:** React (to be built in Phase 11)

**Views:**
- **Dashboard:** Overall health, active incidents, stats
- **Incidents:** List and detail views
- **Topology:** Interactive network graph with highlights
- **Alarms:** Detailed alarm view with suppression info
- **Simulator:** Scenario control and event generation
- **Analytics:** MTTD, MTTI, MTTR, incident trends

## Data Flow Example: Interface Failure

```
1. Simulator generates: Interface GigabitEthernet0/1 on CORE-R1 DOWN

2. Collector receives event, publishes to Kafka (netresolve.events)

3. Normalizer:
   - Parses event
   - Creates Alarm: type=INTERFACE_DOWN, device=CORE-R1, severity=CRITICAL
   - Publishes to Kafka (netresolve.alarms)

4. Correlation Engine:
   - Receives alarm
   - Creates new correlation group
   - Waits for downstream alarms

5. Seconds later, devices downstream detect failures:
   - DIST-R1 can't reach CORE-R1 → DEVICE_UNREACHABLE alarm
   - ACCESS-SW1 can't reach DIST-R1 → DEVICE_UNREACHABLE alarm
   - ACCESS-SW2 can't reach DIST-R1 → DEVICE_UNREACHABLE alarm

6. Correlator receives alarms:
   - Calculates correlation with initial alarm
   - Score: high temporal proximity + topological adjacency
   - Groups all 4 alarms into single correlation group

7. RCA Engine:
   - Identifies CORE-R1 interface alarm as earliest
   - Calculates blast radius: {DIST-R1, ACCESS-SW1, ACCESS-SW2}
   - Validates: all affected devices ARE downstream ✓
   - Confidence: 0.92 (high)
   - Reasoning: "First failure detected on CORE-R1. All downstream devices 
     show unreachable alarms appearing after. Topology confirms dependency chain."

8. Suppression Engine:
   - Root cause: CORE-R1 interface alarm (VISIBLE)
   - Secondary: 3 device unreachable alarms (SUPPRESSED)

9. Incident Manager:
   - Creates Incident with state=OPEN
   - Adds 4 alarms: 1 root cause + 3 suppressed
   - Updates to state=ROOT_CAUSE_IDENTIFIED
   - RCA confidence: 0.92

10. Dashboard shows:
    - Incident #INC-001: CRITICAL
    - Root Cause: CORE-R1 GigabitEthernet0/1 DOWN
    - Affected: 3 devices
    - Suppressed: 3 alarms
    - Confidence: 92%
    - Topology: CORE-R1 highlighted, affected devices highlighted

11. Operator fixes CORE-R1 interface

12. Simulator generates: Interface UP event

13. Normalizer creates recovery alarm

14. RCA recognizes recovery signal matches root cause device

15. Incident Manager marks incident RESOLVED

16. Dashboard updates, removes from active list
```

## Key Design Decisions

### 1. Kafka for Event Streaming
- **Why:** Decouples components, enables horizontal scaling, built-in replay
- **Alternative:** Direct processing (simpler but less resilient)

### 2. Multi-Stage Pipeline
- **Why:** Each component has single responsibility, testable independently
- **Alternative:** Monolithic processor (less modular)

### 3. Topology-First RCA
- **Why:** Network changes are structural; topology is authoritative
- **Alternative:** Pure ML (less interpretable, requires labeled data)

### 4. PostgreSQL with JSON
- **Why:** Structured data in relational tables, flexible metadata in JSON columns
- **Alternative:** NoSQL (less queryable), Time-series DB (overkill for this volume)

### 5. Normalization Before Correlation
- **Why:** Standardize diverse event sources, enrich early
- **Alternative:** Raw event correlation (loses information)

## Scalability Considerations

**Current Design:** Local development, single instance.

**Scaling Opportunities:**
- **Kafka:** Multiple consumers per component (horizontal scale)
- **Database:** Read replicas, partitioned tables (millions of alarms)
- **RCA:** Cache topology, parallelize blast radius calculation
- **API:** Load balancer, multiple instances

## Integration Points

**External Systems:**
- SNMP collectors → Event Collector
- Syslog servers → Event Collector
- Ticketing systems → Incident Manager API
- CMDB → Topology service
- Monitoring → Metrics endpoint

## Security Considerations

**Production Requirements:**
- TLS for Kafka
- Database encryption
- API authentication
- RBAC for dashboard
- Audit logging

**Current State:** Local development (no security hardening).
