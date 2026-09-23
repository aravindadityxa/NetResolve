"""Prometheus metrics endpoint."""

from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.core.logging import logger
from app.core.database import SessionLocal
from app.models.alarm import Alarm
from app.models.incident import Incident

router = APIRouter(tags=["Metrics"])


@router.get("/metrics", response_class=str)
async def get_metrics():
    """Get Prometheus metrics in text format."""
    try:
        db = SessionLocal()

        # Query statistics
        total_alarms = db.query(Alarm).count()
        open_alarms = db.query(Alarm).filter(Alarm.status == "open").count()
        suppressed_alarms = db.query(Alarm).filter(Alarm.status == "suppressed").count()
        acked_alarms = db.query(Alarm).filter(Alarm.status == "acknowledged").count()

        critical_alarms = db.query(Alarm).filter(Alarm.severity == "critical").count()
        major_alarms = db.query(Alarm).filter(Alarm.severity == "major").count()
        minor_alarms = db.query(Alarm).filter(Alarm.severity == "minor").count()

        total_incidents = db.query(Incident).count()
        active_incidents = db.query(Incident).filter(
            Incident.status.in_(["open", "correlated", "active"])
        ).count()
        resolved_incidents = db.query(Incident).filter(
            Incident.status == "resolved"
        ).count()

        db.close()

        # Build Prometheus metrics
        metrics = [
            '# HELP netresolve_alarms_total Total number of alarms',
            '# TYPE netresolve_alarms_total counter',
            f'netresolve_alarms_total {total_alarms}',
            '',
            '# HELP netresolve_alarms_open Active open alarms',
            '# TYPE netresolve_alarms_open gauge',
            f'netresolve_alarms_open {open_alarms}',
            '',
            '# HELP netresolve_alarms_suppressed Suppressed alarms',
            '# TYPE netresolve_alarms_suppressed gauge',
            f'netresolve_alarms_suppressed {suppressed_alarms}',
            '',
            '# HELP netresolve_alarms_acknowledged Acknowledged alarms',
            '# TYPE netresolve_alarms_acknowledged gauge',
            f'netresolve_alarms_acknowledged {acked_alarms}',
            '',
            '# HELP netresolve_alarms_by_severity Alarms by severity',
            '# TYPE netresolve_alarms_by_severity gauge',
            f'netresolve_alarms_by_severity{{severity="critical"}} {critical_alarms}',
            f'netresolve_alarms_by_severity{{severity="major"}} {major_alarms}',
            f'netresolve_alarms_by_severity{{severity="minor"}} {minor_alarms}',
            '',
            '# HELP netresolve_incidents_total Total incidents',
            '# TYPE netresolve_incidents_total counter',
            f'netresolve_incidents_total {total_incidents}',
            '',
            '# HELP netresolve_incidents_active Active incidents',
            '# TYPE netresolve_incidents_active gauge',
            f'netresolve_incidents_active {active_incidents}',
            '',
            '# HELP netresolve_incidents_resolved Resolved incidents',
            '# TYPE netresolve_incidents_resolved counter',
            f'netresolve_incidents_resolved {resolved_incidents}',
            '',
            '# HELP netresolve_suppression_ratio Alarm suppression ratio',
            '# TYPE netresolve_suppression_ratio gauge',
            f'netresolve_suppression_ratio {suppressed_alarms / total_alarms if total_alarms > 0 else 0:.4f}',
            '',
        ]

        return "\n".join(metrics)
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
