# Event Collection and Normalization Pipeline

## Overview

The event pipeline is the first stage of the NetResolve processing flow. It collects events from various sources, normalizes them, and publishes to Kafka for downstream processing.

```
Network Simulator   → Event Collector → Kafka (events)  → Alarm Ingester → Kafka (alarms)
     (or SNMP)         (Threading)         (Pub/Sub)      (Normalization)    (Pub/Sub)
                            ↓
                      PostgreSQL (store)
```

## Components

### 1. Event Collector (`app/messaging/collector.py`)

**Purpose:** Collects events from various sources and publishes to Kafka.

**Sources Supported:**
- Network Simulator (primary for local testing)
- SNMP Traps (framework ready, needs implementation)
- Syslog (framework ready, needs implementation)

**Implementation Details:**

```python
from app.messaging import get_collector

# Start collector (called automatically via app lifespan)
collector = get_collector()
collector.start()

# Get stats
event_count = collector.get_event_count()

# Stop collector
collector.stop()
```

**Simulator Integration:**

- Polls simulator for new events every 500ms
- Creates `NetworkEvent` records in PostgreSQL
- Publishes events to Kafka `netresolve.events` topic
- Thread-safe collection with event deduplication

**Event Flow:**
```
Simulator Event
    ↓
EventCollector._collect_simulator_events()
    ↓
EventService.create_event()  → PostgreSQL (network_events table)
    ↓
KafkaEventProducer.send_event()  → Kafka (netresolve.events topic)
    ↓
Complete
```

### 2. Kafka Event Topics

**Topic: `netresolve.events`**

Raw network events from any source.

Schema:
```json
{
  "event_id": "SIM-1234567890-1",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "source": "simulator",
  "device_id": "CORE-R1",
  "device_hostname": "CORE-R1",
  "event_type": "interface_down",
  "interface_id": "GigabitEthernet0/1",
  "severity": "major",
  "message": "Interface GigabitEthernet0/1 on CORE-R1 changed to DOWN",
  "raw_data": {
    "additional": "fields"
  }
}
```

**Topic: `netresolve.alarms`**

Normalized alarms after ingestion.

Schema:
```json
{
  "id": "alarm-uuid",
  "event_id": "SIM-1234567890-1",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "device_id": "CORE-R1",
  "device_hostname": "CORE-R1",
  "interface_id": "GigabitEthernet0/1",
  "alarm_type": "interface_down",
  "severity": "major",
  "status": "open",
  "message": "Interface GigabitEthernet0/1 on CORE-R1 changed to DOWN",
  "source": "simulator",
  "occurrence_count": 1
}
```

### 3. Event Normalizer (`app/messaging/normalizer.py`)

**Purpose:** Converts raw events into standardized alarm format.

**Responsibilities:**
- Map event types to alarm types
- Map severity levels
- Validate required fields
- Create correlation IDs (later used for grouping)
- Extract correlation hints

**Event Type Mapping:**

| Event Type | Alarm Type |
|-----------|-----------|
| interface_down | INTERFACE_DOWN |
| interface_recovery | INTERFACE_RECOVERY |
| device_unreachable | DEVICE_UNREACHABLE |
| device_recovery | DEVICE_RECOVERY |
| high_latency | HIGH_LATENCY |
| packet_loss | PACKET_LOSS |
| link_flapping | LINK_FLAPPING |
| dependency_failure | DEPENDENCY_FAILURE |

**Severity Mapping:**

| Event Severity | Alarm Severity |
|-----------|-----------|
| critical | CRITICAL |
| major | MAJOR |
| minor | MINOR |
| warning | WARNING |
| informational | INFORMATIONAL |
| debug | DEBUG |

**Usage:**

```python
from app.messaging.normalizer import EventNormalizer

# Normalize single event
alarm = EventNormalizer.normalize(event_dict)

# Normalize batch
alarms = EventNormalizer.batch_normalize(event_list)

# Get correlation hints
hints = EventNormalizer.get_correlation_hints(event_dict)
```

### 4. Alarm Ingester (`app/messaging/alarm_ingester.py`)

**Purpose:** Consumes events, normalizes to alarms, and publishes to alarm topic.

**Process:**

```
1. Kafka Consumer listens to netresolve.events topic
2. For each event:
   a. Check if already processed (idempotency)
   b. Normalize event to alarm using EventNormalizer
   c. Check for duplicates (deduplication window: 5 minutes)
   d. Create Alarm in PostgreSQL
   e. Publish normalized alarm to Kafka (netresolve.alarms)
3. Repeat
```

**Deduplication Logic:**

Within 5-minute window, if same device and same alarm type exist:
- Increment occurrence_count
- Update last_seen timestamp
- Don't create duplicate alarm

**Implementation Details:**

```python
from app.messaging import get_ingester

# Start ingester (called automatically via app lifespan)
ingester = get_ingester()
ingester.start()

# Get stats
alarm_count = ingester.alarm_count

# Stop ingester
ingester.stop()
```

## Event Flow Example

**Scenario:** Core Interface Failure

```
T+0s: Simulator generates "interface down" event
      event_id: SIM-1234567890-1
      device_hostname: CORE-R1
      interface_id: GigabitEthernet0/1

T+0.1s: EventCollector.collect_simulator_events() picks up event
        → Creates NetworkEvent in PostgreSQL
        → Publishes to Kafka (netresolve.events)

T+0.2s: AlarmIngester.consume() receives event from Kafka
        → EventNormalizer.normalize() converts to alarm
        → AlarmService.deduplicate_alarm() checks for duplicates
        → Creates Alarm in PostgreSQL
        → Publishes to Kafka (netresolve.alarms)
        alarm_id: abc-123-def-456
        alarm_type: interface_down
        severity: major

T+0.3s: Downstream systems consume alarm from netresolve.alarms
        → Correlation engine (Phase 6)
        → RCA engine (Phase 7)
        → Suppression engine (Phase 8)

T+2s: DIST-R1 detects unreachable
      → Similar flow creates DEVICE_UNREACHABLE alarm

T+3s: ACCESS-SW1 detects unreachable
      → Similar flow creates DEVICE_UNREACHABLE alarm

T+4s: Correlation engine sees 3 alarms (1 interface + 2 device unreachable)
      → Correlates together
      → RCA identifies CORE-R1 interface as root cause
      → Suppression engine marks other 2 as secondary
      → Creates single incident
```

## Kafka Configuration

**Docker Compose:**
```yaml
kafka:
  image: confluentinc/cp-kafka:7.5.0
  ports:
    - "9092:9092"
  environment:
    KAFKA_BOOTSTRAP_SERVERS: kafka:29092
    KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
```

**Python Client:**
```python
from app.core.config import settings

# Bootstrap servers from settings
settings.kafka_bootstrap_servers = "localhost:9092"

# Topics from settings
settings.kafka_event_topic = "netresolve.events"
settings.kafka_alarm_topic = "netresolve.alarms"
```

## Monitoring the Pipeline

### Via REST API (Phase 10)

```bash
# Get collector status
curl http://localhost:8000/api/background/status

# Get recent events
curl http://localhost:8000/api/events?limit=20

# Get recent alarms
curl http://localhost:8000/api/alarms?limit=20
```

### Via Kafka Console

```bash
# Listen to events topic
kafka-console-consumer --bootstrap-server localhost:9092 \
  --topic netresolve.events \
  --from-beginning

# Listen to alarms topic
kafka-console-consumer --bootstrap-server localhost:9092 \
  --topic netresolve.alarms \
  --from-beginning
```

### Logs

```bash
# All events collected
docker logs netresolve-api | grep "Event collected"

# All alarms created
docker logs netresolve-api | grep "Created and published alarm"
```

## Error Handling

**Event Collection Errors:**
- Missing required fields → Event skipped with warning
- Database connection error → Retry with backoff
- Kafka publish failure → Retry up to 3 times
- Graceful degradation if Kafka unavailable

**Normalization Errors:**
- Unknown event type → Use default alarm type
- Invalid severity → Use WARNING as default
- Missing timestamp → Use current time
- Invalid timestamps → Skip event

**Ingestion Errors:**
- Duplicate event (already in DB) → Skip silently
- Normalization failure → Log and skip
- Database error → Log and skip
- Kafka publish failure → Log and continue

## Performance Characteristics

**Single Event Latency:**
- Collection: ~0.5s (polling interval)
- Normalization: ~1-5ms
- Publishing: ~10-50ms
- Total: ~500-600ms

**Throughput:**
- Tested: 1000 events/second
- Bottleneck: Database writes for network_events
- Optimization: Batch inserts, async writes

**Memory Usage:**
- Collector: ~5MB (event history)
- Ingester: ~2MB (per consumer)
- Kafka buffers: ~10-20MB per producer/consumer

## Integration Points

### Adding SNMP Trap Collection

```python
class SNMPTrapCollector:
    def __init__(self):
        self.trap_receiver = SNMPServer(...)
        self.producer = KafkaEventProducer()
    
    def on_trap_received(self, trap):
        event = self._parse_trap(trap)
        self.producer.send_event(event)
```

### Adding Syslog Collection

```python
class SyslogCollector:
    def __init__(self):
        self.syslog_server = SyslogServer(...)
        self.producer = KafkaEventProducer()
    
    def on_message(self, message):
        event = self._parse_syslog(message)
        self.producer.send_event(event)
```

### Custom Event Source

```python
def create_custom_event():
    event = {
        "event_id": "CUSTOM-001",
        "timestamp": datetime.utcnow().isoformat(),
        "source": "custom_system",
        "device_id": "dev-1",
        "device_hostname": "my-router",
        "event_type": "interface_down",
        "interface_id": "eth0",
        "severity": "major",
        "message": "Custom event from external system",
    }
    
    producer = KafkaEventProducer()
    producer.send_event(event)
```

## Testing the Pipeline

### Manual Test

```bash
# Start all services
docker-compose up -d

# Run simulator scenario
curl -X POST http://localhost:8000/api/simulator/scenarios/core_interface_failure

# Watch events being created
docker logs -f netresolve-api | grep "Event"

# Watch alarms being created
docker logs -f netresolve-api | grep "Created and published alarm"

# Check database
psql postgresql://netresolve:netresolve@localhost:5432/netresolve
> SELECT COUNT(*) FROM network_events;
> SELECT COUNT(*) FROM alarms;
```

### Automated Test

See Phase 13 (Testing) for comprehensive integration tests.

## Troubleshooting

### Events Not Being Collected

```bash
# Check collector is running
curl http://localhost:8000/api/background/status | jq .collector

# Check simulator has events
curl http://localhost:8000/api/simulator/history | jq length

# Check logs
docker logs netresolve-api | grep "Event collector"
```

### Events Not Being Normalized

```bash
# Check Kafka is running
docker-compose ps kafka

# Check alarm ingester is running
curl http://localhost:8000/api/background/status | jq .ingester

# Check logs for normalization errors
docker logs netresolve-api | grep "normalize"
```

### Duplicate Alarms Being Created

```bash
# Check deduplication logic
# May indicate deduplication window is too short (300s default)

# Verify alarms are being deduplicated
SELECT COUNT(*) FROM alarms 
WHERE alarm_type = 'interface_down' 
AND occurrence_count > 1;
```

## Next Phase

Phase 5: Alarm Correlation Engine - Groups related alarms based on topology and timing.
