# NetResolve

**Automated Network Root Cause Analysis & Alarm Suppression Platform**

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)

## Problem Statement

When a network fails, operators receive a cascade of alarms—sometimes dozens or hundreds. A single physical fault can trigger secondary alarms across multiple devices and services. Manually correlating these alarms takes 15-30 minutes, during which time the root cause remains unclear and secondary damage can occur.

**NetResolve solves this** by automatically:
1. Collecting network events and normalizing them into alarms
2. Correlating related alarms using topology and timing analysis
3. Identifying the probable root cause using evidence-based scoring
4. Suppressing secondary alarms to reduce noise
5. Creating a single meaningful incident from an alarm storm

## Key Features

✓ **Automated Root Cause Analysis** - Topology-aware RCA identifies the primary fault
✓ **Intelligent Alarm Correlation** - Multi-signal scoring groups related alarms
✓ **Automatic Alarm Suppression** - Secondary alarms hidden, root cause visible
✓ **Topology-Aware** - Understands device dependencies and cascade patterns
✓ **Realistic Simulator** - Built-in network simulator for demos and testing
✓ **REST APIs** - Full HTTP API for integration
✓ **Professional Dashboard** - Real-time incident view, topology visualization
✓ **Prometheus Metrics** - Observability and monitoring
✓ **Local-First** - Runs entirely locally, no cloud APIs required
✓ **Explainable** - Shows reasoning for RCA decisions, not a black box

## Architecture

```
Network Simulator / SNMP / Syslog
           ↓
    Event Collector
           ↓
   Kafka Event Bus
           ↓
Event Normalization
           ↓
 Alarm Correlation
           ↓
   Root Cause Analysis
           ↓
 Alarm Suppression
           ↓
 Incident Management
           ↓
    REST API / Dashboard
```

**Technologies:**
- **Language:** Python 3.11+
- **Backend:** FastAPI + SQLAlchemy
- **Database:** PostgreSQL + SQLite (local)
- **Messaging:** Apache Kafka
- **Monitoring:** Prometheus + Grafana
- **Containerization:** Docker + Docker Compose
- **Topology:** NetworkX

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)
- ~2GB disk space, ~1GB RAM

### One-Line Start

```bash
# Clone and start
git clone https://github.com/your-org/netresolve.git
cd netresolve
docker-compose up -d

# Initialize database
docker exec netresolve-api python scripts/init_db.py

# Run demo scenario
curl -X POST http://localhost:8000/api/simulator/scenarios/core_interface_failure

# View dashboard
open http://localhost:3000  # Grafana (admin/admin)
open http://localhost:8000/docs  # API docs
```

### Services

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5432 | Database |
| Kafka | 9092 | Event streaming |
| Zookeeper | 2181 | Kafka coordination |
| NetResolve API | 8000 | REST API + Simulator |
| Prometheus | 9090 | Metrics |
| Grafana | 3000 | Dashboard |

## How It Works

### Example: Core Router Interface Failure

**Time T+0s:**
- Operator shutdowns CORE-R1 GigabitEthernet0/1 (simulated failure)
- Network simulator generates event

**Time T+0.5s:**
```
Event Collector → PostgreSQL, Kafka
```

**Time T+1s:**
```
Alarm Ingester:
  Normalize: interface_down → INTERFACE_DOWN alarm (MAJOR)
  Publish: → Kafka netresolve.alarms
  Store: → PostgreSQL alarms table
```

**Time T+2s:**
```
Downstream devices detect unreachability:
  DIST-R1 → DEVICE_UNREACHABLE (CRITICAL)
  ACCESS-SW1 → DEVICE_UNREACHABLE (CRITICAL)
  ACCESS-SW2 → DEVICE_UNREACHABLE (CRITICAL)
```

**Time T+5s:**
```
Correlation Engine:
  ✓ Group 4 alarms by temporal + topological + dependency scores
  ✓ Assign correlation_id to all 4
```

**Time T+10s:**
```
RCA Engine:
  ✓ Analyze correlation group
  ✓ Score each alarm as potential root cause using:
    - Temporal factors (which alarm occurred first)
    - Topological factors (device dependencies)
    - Cascade factors (alarm propagation patterns)
    - Severity factors
  ✓ Select: CORE-R1 interface as root cause (89% confidence in this scenario)
  ✓ Calculate: 3 affected devices, 3 suppressed alarms
  ✓ Generate reasoning with evidence
```

**Time T+15s:**
```
Suppression Engine:
  ✓ Mark 3 secondary alarms as SUPPRESSED
  ✓ Parent relationship: DIST-R1 → CORE-R1 interface
```

**Time T+20s:**
```
Incident Manager:
  ✓ Create Incident: ID=INC-0001, Status=ACTIVE
  ✓ Root Cause: CORE-R1 GigabitEthernet0/1 DOWN
  ✓ Confidence: 89%
  ✓ Affected: [DIST-R1, ACCESS-SW1, ACCESS-SW2]
  ✓ Related Alarms: 4 total (1 visible, 3 suppressed)
  ✓ Timeline: 4 events
```

**Dashboard shows:**
```
INCIDENT #INC-0001 - CRITICAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Root Cause: CORE-R1 GigabitEthernet0/1 DOWN
Confidence: 89% (simulator scenario)
Status: ACTIVE
Affected Devices: 3
Suppressed Alarms: 3

Reasoning:
  ✓ First event detected on CORE-R1
  ✓ Interface is upstream of 3 affected devices
  ✓ All downstream devices show unreachable (cascade pattern)
  ✓ Topology confirms dependency relationship

Timeline:
  T+0s: CORE-R1 interface DOWN
  T+2s: DIST-R1 unreachable
  T+3s: ACCESS-SW1 unreachable
  T+4s: ACCESS-SW2 unreachable
```

## Demo Scenarios

11 built-in scenarios demonstrate different failure modes:

| Scenario | Event | Expected Result |
|----------|-------|-----------------|
| Core Interface Failure | CORE-R1 Gi0/1 down | 1 root cause + 3 secondary |
| Core Interface Recovery | CORE-R1 Gi0/1 up | Incident resolves |
| Distribution Router Failure | DIST-R1 unreachable | 1 root + 2 secondary |
| Distribution Router Recovery | DIST-R1 recovers | Incident resolves |
| Access Switch Failure | ACCESS-SW1 unreachable | Single alarm (leaf) |
| Access Switch Recovery | ACCESS-SW1 recovers | Incident resolves |
| Link Flapping | Interface flaps 5x | Link flapping alarm |
| High Latency | 250ms latency | Quality alarm |
| Packet Loss | 8.5% loss | Quality alarm |
| Cascading Dual Failure | Both CORE interfaces fail | 2 root causes or combined |
| Network Recovery | All devices recover | Full cascade resolution |

**Run a scenario:**
```bash
# Via API
curl -X POST http://localhost:8000/api/simulator/scenarios/core_interface_failure

# View results
curl http://localhost:8000/api/incidents
```

## Configuration

Edit `.env` to customize:

```env
# Database
DATABASE_URL=postgresql://netresolve:netresolve@localhost:5432/netresolve

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_ALARM_TOPIC=netresolve.alarms
KAFKA_EVENT_TOPIC=netresolve.events

# API
API_HOST=0.0.0.0
API_PORT=8000

# Simulator
SIMULATOR_ENABLED=true
SIMULATOR_EVENT_INTERVAL=5

# Logging
LOG_LEVEL=INFO
ENVIRONMENT=development
```

## REST API Endpoints

### Health & Status
- `GET /api/health` - Health check
- `GET /api/status` - System status

### Devices & Topology
- `GET /api/devices` - List devices
- `GET /api/devices/{id}` - Get device details
- `GET /api/topology` - Get network topology
- `GET /api/topology/blast-radius/{device_id}` - Calculate impact

### Alarms
- `GET /api/alarms` - List alarms (filters: status, severity, device)
- `GET /api/alarms/{id}` - Get alarm details
- `POST /api/alarms/{id}/acknowledge` - Acknowledge alarm
- `GET /api/alarms/statistics` - Alarm statistics

### Incidents
- `GET /api/incidents` - List incidents
- `GET /api/incidents/{id}` - Get incident details
- `GET /api/incidents/{id}/timeline` - Event timeline
- `GET /api/incidents/{id}/suppressed-alarms` - Suppressed alarms
- `POST /api/incidents/{id}/resolve` - Resolve incident

### Correlation
- `GET /api/correlation/groups` - List correlation groups
- `GET /api/correlation/{group_id}` - Get group details

### RCA
- `POST /api/rca/{group_id}/analyze` - Run RCA analysis
- `GET /api/rca/{group_id}/reasoning` - Get RCA reasoning
- `GET /api/rca/{group_id}/remediation` - Get remediation suggestions

### Simulator
- `GET /api/simulator/status` - Simulator status
- `GET /api/simulator/scenarios` - List available scenarios
- `POST /api/simulator/scenarios/{name}` - Run scenario
- `GET /api/simulator/history` - Event history
- `DELETE /api/simulator/history` - Clear history

### Metrics
- `GET /api/metrics` - Prometheus metrics

## Development

### Setup

```bash
# Clone
git clone https://github.com/your-org/netresolve.git
cd netresolve

# Virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate.bat  # Windows

# Install
pip install -r requirements.txt

# Database
python scripts/init_db.py
python scripts/migrate.py upgrade

# Run
uvicorn app.main:app --reload
```

### Project Structure

```
netresolve/
├── app/
│   ├── api/              # FastAPI routes
│   ├── correlation/      # Alarm correlation engine
│   ├── core/             # Config, logging, database
│   ├── messaging/        # Kafka, event collection
│   ├── models/           # SQLAlchemy models
│   ├── rca/              # Root cause analysis
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   ├── simulator/        # Network simulator
│   ├── suppression/      # Alarm suppression
│   ├── topology/         # Topology analysis
│   └── main.py           # Application entry
├── tests/                # Comprehensive tests
├── migrations/           # Database migrations
├── docs/                 # Documentation
├── scripts/              # Utilities
├── docker-compose.yml    # Local stack
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

### Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=app tests/

# Specific test file
pytest tests/test_correlation.py

# Watch mode
pytest-watch
```

## Documentation

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design and component relationships
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Installation, deployment, and testing
- **[docs/SIMULATOR.md](docs/SIMULATOR.md)** - Network simulator guide and scenarios
- **[docs/EVENT_PIPELINE.md](docs/EVENT_PIPELINE.md)** - Event collection and normalization flow
- **[docs/CORRELATION_AND_RCA.md](docs/CORRELATION_AND_RCA.md)** - Correlation and RCA algorithms

## Performance

NetResolve is designed for efficient processing of network events and correlation:

| Component | Behavior |
|-----------|----------|
| Event collection latency | ~500ms (simulator) |
| Normalization latency | ~1-5ms |
| Correlation latency | ~10-50ms |
| RCA analysis latency | ~50-200ms |
| Total E2E latency | ~600ms (typical) |
| Alarm throughput | Tested up to 1000+ alarms/sec |
| Correlation group capacity | 100+ groups |

*Note: These measurements are from local development environment with simulator. Production performance will vary based on event sources, network latency, and hardware.*

## Limitations & Future Work

### Current Limitations
- Single-machine deployment (no horizontal scaling)
- Simulated network only (no real SNMP/Syslog integration yet)
- Basic topology model (no service dependencies)
- No ML-based RCA (deterministic only)
- No persistent event history (in-memory only)

### Future Enhancements
- Multi-instance deployment with Kubernetes
- Real SNMP trap and syslog collectors
- Service dependency mapping
- Machine learning RCA enhancement
- Event retention and replay
- Advanced visualization (Grafana plugins)
- Webhook notifications (Slack, PagerDuty)
- Integration with ticketing systems (Jira, ServiceNow)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes and test (`pytest`)
4. Commit (`git commit -am 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## Testing the Complete System

```bash
# Terminal 1: Start services
docker-compose up

# Terminal 2: Initialize database
docker exec netresolve-api python scripts/init_db.py

# Terminal 3: Run demo
curl -X POST http://localhost:8000/api/simulator/scenarios/core_interface_failure

# Terminal 4: Watch results
watch -n 1 'curl -s http://localhost:8000/api/incidents | jq .'

# View on dashboard
open http://localhost:3000  # Grafana
open http://localhost:8000/docs  # Swagger UI
```

## Support

- **Documentation:** See [docs/](docs/) directory
- **Issues:** GitHub Issues
- **Discussions:** GitHub Discussions
- **Email:** support@netresolve.dev

## License

MIT License - see [LICENSE](LICENSE) file for details

## Authors

- NetResolve Team

---

**Built with ❤️ for network operations teams**

**Making network troubleshooting faster, smarter, and less stressful.**
