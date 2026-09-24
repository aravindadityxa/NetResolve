"""Incident management endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import List
from datetime import datetime

from app.core.logging import logger
from app.core.database import SessionLocal
from app.core.constants import IncidentState
from app.models.incident import Incident, TimelineEvent
from app.models.alarm import Alarm
from app.schemas.incident import IncidentSchema, IncidentDetailSchema
from app.services.incident_service import IncidentService

router = APIRouter(tags=["Incidents"])


@router.get("/incidents", response_model=List[IncidentSchema])
async def list_incidents(
    state: str = Query(None, description="Filter by state"),
    severity: str = Query(None, description="Filter by severity"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List incidents."""
    try:
        db = SessionLocal()
        query = db.query(Incident)

        if state:
            query = query.filter(Incident.state == state)
        if severity:
            query = query.filter(Incident.severity == severity)

        incidents = (
            query.order_by(Incident.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        db.close()

        return [IncidentSchema.from_orm(i) for i in incidents]
    except Exception as e:
        logger.error(f"Error listing incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/incidents/{incident_id}", response_model=IncidentDetailSchema)
async def get_incident(incident_id: str):
    """Get incident details."""
    try:
        db = SessionLocal()
        incident = db.query(Incident).filter(Incident.id == incident_id).first()

        if not incident:
            db.close()
            raise HTTPException(status_code=404, detail="Incident not found")

        db.close()
        return IncidentDetailSchema.from_orm(incident)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting incident {incident_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/incidents/{incident_id}/timeline")
async def get_incident_timeline(incident_id: str):
    """Get incident timeline events."""
    try:
        db = SessionLocal()
        incident = db.query(Incident).filter(Incident.id == incident_id).first()

        if not incident:
            db.close()
            raise HTTPException(status_code=404, detail="Incident not found")

        events = (
            db.query(TimelineEvent)
            .filter(TimelineEvent.incident_id == incident_id)
            .order_by(TimelineEvent.timestamp)
            .all()
        )

        db.close()

        return {
            "incident_id": incident_id,
            "event_count": len(events),
            "events": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "event_type": e.event_type,
                    "description": e.description,
                    "severity": e.severity,
                }
                for e in events
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting incident timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/incidents/{incident_id}/suppressed-alarms")
async def get_suppressed_alarms(incident_id: str):
    """Get suppressed alarms for incident."""
    try:
        db = SessionLocal()
        incident = db.query(Incident).filter(Incident.id == incident_id).first()

        if not incident:
            db.close()
            raise HTTPException(status_code=404, detail="Incident not found")

        if not incident.root_cause_alarm_id:
            db.close()
            return {"incident_id": incident_id, "suppressed_alarms": []}

        suppressed = (
            db.query(Alarm)
            .filter(Alarm.parent_alarm_id == incident.root_cause_alarm_id)
            .filter(Alarm.status == "suppressed")
            .all()
        )

        db.close()

        return {
            "incident_id": incident_id,
            "count": len(suppressed),
            "suppressed_alarms": [
                {
                    "id": a.id,
                    "device_id": a.device_id,
                    "alarm_type": a.alarm_type,
                    "severity": a.severity,
                    "message": a.message,
                    "created_at": a.created_at.isoformat(),
                }
                for a in suppressed
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting suppressed alarms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/incidents/{incident_id}/resolve")
async def resolve_incident(incident_id: str):
    """Resolve an incident."""
    try:
        db = SessionLocal()
        incident = db.query(Incident).filter(Incident.id == incident_id).first()

        if not incident:
            db.close()
            raise HTTPException(status_code=404, detail="Incident not found")

        incident.state = IncidentState.RESOLVED
        incident.updated_at = datetime.utcnow()
        db.commit()
        db.close()

        logger.info(f"Resolved incident {incident_id}")
        return {"message": "Incident resolved", "incident_id": incident_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))
