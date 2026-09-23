# NetResolve - Deployment & Testing Guide

## Quick Start - Local Development

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Git
- ~2GB disk space

### 30-Second Startup

```bash
# 1. Clone the repository
git clone <repo-url>
cd netresolve

# 2. Start all services
docker-compose up -d

# 3. Initialize database
docker exec netresolve-api python scripts/init_db.py

# 4. Run a demo scenario
curl -X POST http://localhost:8000/api/simulator/scenarios/core_interface_failure

# 5. View results
curl http://localhost:8000/api/incidents | python -m json.tool
```

That's it! The system is running.

### Services Running

```
PostgreSQL      → localhost:5432 (netresolve/netresolve)
Kafka/Zookeeper → localhost:9092, 2181
NetResolve API  → localhost:8000
Prometheus      → localhost:9090
Grafana         → localhost:3000 (admin/admin)
```

## Local Development Setup

### Using Python venv (for development)

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate.bat  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file
cp .env.example .env

# 4. Start services (only PostgreSQL + Kafka needed)
docker-compose up -d postgres kafka zookeeper

# 5. Initialize database
python scripts/init_db.py
python scripts/migrate.py upgrade

# 6. Run API server
uvicorn app.main:app --reload

# 7. In another terminal, run the event collector
python -c "from app.services.background_service import get_background_manager; mgr = get_background_manager(); mgr.start(); import time; time.sleep(999999)"
```

API will be at: http://localhost:8000
API Docs: http://localhost:8000/docs
Health check: http://localhost:8000/api/health

## Running Tests

### Basic Test Commands

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app tests/

# Run specific test file
pytest tests/test_correlation.py -v

# Run tests matching pattern
pytest tests/ -k "test_alarm" -v

# Run with markers
pytest -m "integration"
```

### Test Structure

```
tests/
├── test_alarm_service.py      # Alarm creation, deduplication
├── test_correlation.py         # Correlation scoring
├── test_rca.py                # Root cause analysis
├── test_suppression.py        # Alarm suppression
├── test_incident_service.py   # Incident lifecycle
├── test_api_endpoints.py      # REST API
└── test_simulator.py          # Simulator scenarios
```

### Coverage Requirements

- Target: 80%+ coverage
- Run: `pytest --cov=app --cov-report=html`
- Report: `htmlcov/index.html`

## End-to-End Testing

### Test Scenario: Core Interface Failure

1. **Start Services**
   ```bash
   docker-compose up -d
   ```

2. **Initialize Database**
   ```bash
   docker exec netresolve-api python scripts/init_db.py
   ```

3. **Run Scenario**
   ```bash
   curl -X POST http://localhost:8000/api/simulator/scenarios/core_interface_failure
   ```

4. **Verify Events Collected**
   ```bash
   curl http://localhost:8000/api/simulator/history | jq .
   # Should show ~4 events
   ```

5. **Check Alarms Created**
   ```bash
   curl http://localhost:8000/api/alarms | jq .
   # Should show 4 alarms:
   # - 1 INTERFACE_DOWN (MAJOR)
   # - 3 DEVICE_UNREACHABLE (CRITICAL)
   ```

6. **Verify Correlation**
   ```bash
   curl http://localhost:8000/api/correlation/groups | jq .
   # Should show 1 correlation group with 4 alarms
   ```

7. **Analyze RCA**
   ```bash
   CORR_ID=$(curl -s http://localhost:8000/api/correlation/groups | jq -r '.[0].correlation_id')
   curl http://localhost:8000/api/rca/$CORR_ID/analyze | jq .
   # Should identify INTERFACE_DOWN as root cause (~89% confidence)
   ```

8. **Check Suppression**
   ```bash
   curl http://localhost:8000/api/alarms?status=suppressed | jq .
   # Should show 3 suppressed alarms
   ```

9. **Verify Incident Created**
   ```bash
   curl http://localhost:8000/api/incidents | jq .
   # Should show 1 incident with:
   # - Status: ACTIVE
   # - Root cause identified
   # - 3 affected devices
   # - 3 suppressed alarms
   ```

10. **View Dashboard**
    - Open http://localhost:3000 (Grafana)
    - Login: admin/admin
    - View Incident dashboard

## Performance Testing

### Load Testing - Bulk Alarm Creation

```bash
# Generate 1000 alarms
python -c "
from app.services.alarm_service import AlarmService
from app.core.database import SessionLocal
import time

db = SessionLocal()
service = AlarmService(db)
start = time.time()

for i in range(1000):
    service.create_alarm(
        event_id=f'evt-{i}',
        device_id=f'device-{i % 10}',
        alarm_type='INTERFACE_DOWN',
        severity='major',
        message=f'Test alarm {i}'
    )

elapsed = time.time() - start
print(f'Created 1000 alarms in {elapsed:.2f}s ({1000/elapsed:.0f} alarms/sec)')
"
```

Expected: > 500 alarms/sec

### Latency Testing - RCA Performance

```bash
# Run RCA on various group sizes
python -c "
from app.core.database import SessionLocal
from app.rca.analyzer import RCAAnalyzer
import time

db = SessionLocal()
analyzer = RCAAnalyzer(db)

# For each correlation group, measure analysis time
from app.models.alarm import Alarm
groups = db.query(Alarm.correlation_id).distinct().all()

for (group_id,) in groups[:10]:
    start = time.time()
    result = analyzer.analyze_group(group_id)
    elapsed = (time.time() - start) * 1000
    alarm_count = db.query(Alarm).filter(Alarm.correlation_id == group_id).count()
    print(f'Group {group_id}: {alarm_count} alarms, {elapsed:.1f}ms')
"
```

Expected: 50-200ms for typical groups (5-10 alarms)

## Monitoring & Observability

### Prometheus Metrics

Access metrics at: http://localhost:9090

Key metrics to monitor:
- `netresolve_alarms_open` - Active alarms
- `netresolve_alarms_suppressed` - Suppressed alarms
- `netresolve_incidents_active` - Active incidents
- `netresolve_suppression_ratio` - Suppression effectiveness

### Grafana Dashboards

1. Navigate to http://localhost:3000
2. Login: admin/admin
3. Add Prometheus datasource: http://prometheus:9090
4. Import dashboards:
   - Alarm Overview
   - Incident Timeline
   - RCA Effectiveness
   - Suppression Statistics

### Application Logs

```bash
# View logs from API container
docker logs -f netresolve-api

# Filter by severity
docker logs netresolve-api 2>&1 | grep "ERROR"

# Follow Kafka messages
docker exec netresolve-kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic netresolve.alarms \
  --from-beginning
```

## Troubleshooting

### Database Connection Failed

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Connect to database
psql -h localhost -U netresolve -d netresolve

# View tables
\dt

# Reset database
docker exec netresolve-postgres psql -U netresolve -d netresolve \
  -c "DROP TABLE IF EXISTS alarms CASCADE;"
docker exec netresolve-api python scripts/init_db.py
```

### Kafka Connection Issues

```bash
# Check Kafka is running
docker ps | grep kafka

# List topics
docker exec netresolve-kafka kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --list

# Check topic contents
docker exec netresolve-kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic netresolve.events \
  --from-beginning \
  --max-messages 10
```

### API Not Responding

```bash
# Check API container
docker ps | grep netresolve-api

# Check logs
docker logs netresolve-api

# Restart API
docker restart netresolve-api

# Check health
curl http://localhost:8000/api/health
```

### Simulator Not Generating Events

```bash
# Check simulator is enabled in .env
grep SIMULATOR_ENABLED .env

# Check simulator status
curl http://localhost:8000/api/simulator/status

# Manually trigger event
curl -X POST http://localhost:8000/api/simulator/scenarios/core_interface_failure

# View event history
curl http://localhost:8000/api/simulator/history
```

## Deployment Checklist

### Pre-Deployment

- [ ] All tests passing (`pytest`)
- [ ] Coverage > 80% (`pytest --cov`)
- [ ] Docker images built (`docker-compose build`)
- [ ] Configuration reviewed (`.env`)
- [ ] Database migrations tested (`python scripts/migrate.py upgrade`)
- [ ] Documentation updated

### Production Deployment

```bash
# 1. Clone on production server
git clone <repo-url> /opt/netresolve
cd /opt/netresolve

# 2. Create production .env
cat > .env << EOF
DATABASE_URL=postgresql://user:pass@prod-postgres:5432/netresolve
KAFKA_BOOTSTRAP_SERVERS=prod-kafka:9092
API_HOST=0.0.0.0
API_PORT=8000
ENVIRONMENT=production
LOG_LEVEL=INFO
EOF

# 3. Start services
docker-compose -f docker-compose.prod.yml up -d

# 4. Initialize database (one-time)
docker exec netresolve-api python scripts/init_db.py

# 5. Verify health
curl http://localhost:8000/api/health

# 6. Configure backups
# - PostgreSQL: Daily backups to S3
# - Kafka: Retention policy 7 days minimum
# - Logs: Rotate daily, keep 30 days
```

### Post-Deployment Verification

```bash
# 1. Health check
curl http://localhost:8000/api/health

# 2. Database connectivity
curl http://localhost:8000/api/incidents

# 3. Simulator test
curl -X POST http://localhost:8000/api/simulator/scenarios/core_interface_failure

# 4. Metrics export
curl http://localhost:8000/api/metrics

# 5. Monitor for errors
docker logs -f netresolve-api | grep ERROR
```

## Backup & Recovery

### Database Backup

```bash
# Backup PostgreSQL
docker exec netresolve-postgres pg_dump -U netresolve netresolve > netresolve_backup.sql

# Restore from backup
docker exec -i netresolve-postgres psql -U netresolve netresolve < netresolve_backup.sql
```

### Configuration Backup

```bash
# Backup configuration and migrations
tar -czf netresolve_config.tar.gz \
  .env \
  migrations/ \
  scripts/ \
  docker-compose.yml
```

### Recovery Procedure

```bash
# 1. Stop services
docker-compose down

# 2. Restore PostgreSQL
docker-compose up -d postgres
docker exec -i netresolve-postgres psql -U netresolve netresolve < netresolve_backup.sql

# 3. Start all services
docker-compose up -d

# 4. Verify
curl http://localhost:8000/api/health
curl http://localhost:8000/api/incidents
```

## Scaling Considerations

### Current Deployment (Single-Node)

- Max throughput: 1000+ alarms/sec
- Max correlation groups: 100+
- Max stored alarms: Limited by PostgreSQL disk
- Typical memory: 500MB - 2GB

### Horizontal Scaling

For multi-node deployment:
1. Separate PostgreSQL (managed database)
2. Kafka cluster (3+ brokers)
3. Multiple API instances (load balancer)
4. Dedicated Prometheus instance
5. Dedicated Grafana instance

### Performance Tuning

```bash
# Increase connection pool
# In .env
SQLALCHEMY_POOL_SIZE=20
SQLALCHEMY_MAX_OVERFLOW=40

# Increase Kafka batch size
# In app/messaging/kafka.py
batch_size=1000
batch_timeout_ms=5000

# Enable database query cache
# In .env
REDIS_URL=redis://localhost:6379
```

## Monitoring & Maintenance

### Weekly Tasks
- [ ] Check disk space (PostgreSQL, Kafka)
- [ ] Review error logs
- [ ] Verify backup completion
- [ ] Check metric collection

### Monthly Tasks
- [ ] Archive old alarms (> 90 days)
- [ ] Review and optimize slow queries
- [ ] Update dependencies (`pip install --upgrade -r requirements.txt`)
- [ ] Test recovery procedure

### Quarterly Tasks
- [ ] Performance benchmarking
- [ ] Capacity planning
- [ ] Security audit
- [ ] Documentation update

## Support & Resources

- Documentation: `/docs` directory
- API Docs: http://localhost:8000/docs (Swagger)
- Logs: `docker logs <container-name>`
- Issues: GitHub Issues
- Status: http://localhost:8000/api/status

---

**NetResolve Deployment v1.0**

For production support, refer to the ARCHITECTURE.md and README.md documentation.
