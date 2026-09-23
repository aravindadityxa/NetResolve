"""Alarm management endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from datetime import datetime

from app.core.logging import logger
from app.core.database import SessionLocal
from app.models.alarm import Alarm
from app.schemas.alarm import AlarmSchema, AlarmStatisticsSchema
from app.services.alarm_service import AlarmService

router = APIRouter(tags=["Alarms"])


@router.get("/alarms", response_model=List[AlarmSchema])
async def list_alarms(
    status: str = Query(None, description="Filter by status (open, ack, resolved, suppressed)"),
    severity: str = Query(None, description="Filter by severity"),
    device_id: str = Query(None, description="Filter by device"),
    correlation_id: str = Query(None, description="Filter by correlation group"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List alarms with filtering."""
    try:
        db = SessionLocal()
        query = db.query(Alarm)

        if status:
            query = query.filter(Alarm.status == status)
        if severity:
            query = query.filter(Alarm.severity == severity)
        if device_id:
            query = query.filter(Alarm.device_id == device_id)
        if correlation_id:
            query = query.filter(Alarm.correlation_id == correlation_id)

        alarms = query.order_by(Alarm.created_at.desc()).offset(offset).limit(limit).all()
        db.close()

        return [AlarmSchema.from_orm(a) for a in alarms]
    except Exception as e:
        logger.error(f"Error listing alarms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alarms/{alarm_id}", response_model=AlarmSchema)
async def get_alarm(alarm_id: str):
    """Get alarm details."""
    try:
        db = SessionLocal()
        alarm = db.query(Alarm).filter(Alarm.id == alarm_id).first()
        db.close()

        if not alarm:
            raise HTTPException(status_code=404, detail="Alarm not found")

        return AlarmSchema.from_orm(alarm)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alarm {alarm_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alarms/{alarm_id}/acknowledge")
async def acknowledge_alarm(alarm_id: str):
    """Acknowledge an alarm."""
    try:
        db = SessionLocal()
        alarm = db.query(Alarm).filter(Alarm.id == alarm_id).first()

        if not alarm:
            db.close()
            raise HTTPException(status_code=404, detail="Alarm not found")

        alarm.status = "acknowledged"
        db.commit()
        db.close()

        logger.info(f"Acknowledged alarm {alarm_id}")
        return {"message": "Alarm acknowledged", "alarm_id": alarm_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alarm: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alarms/statistics/summary")
async def get_alarm_statistics() -> Dict[str, Any]:
    """Get alarm statistics."""
    try:
        db = SessionLocal()

        total = db.query(Alarm).count()
        open_alarms = db.query(Alarm).filter(Alarm.status == "open").count()
        acked_alarms = db.query(Alarm).filter(Alarm.status == "acknowledged").count()
        resolved_alarms = db.query(Alarm).filter(Alarm.status == "resolved").count()
        suppressed_alarms = db.query(Alarm).filter(Alarm.status == "suppressed").count()

        # Severity breakdown
        critical = db.query(Alarm).filter(Alarm.severity == "critical").count()
        major = db.query(Alarm).filter(Alarm.severity == "major").count()
        minor = db.query(Alarm).filter(Alarm.severity == "minor").count()

        db.close()

        return {
            "total_alarms": total,
            "by_status": {
                "open": open_alarms,
                "acknowledged": acked_alarms,
                "resolved": resolved_alarms,
                "suppressed": suppressed_alarms,
            },
            "by_severity": {
                "critical": critical,
                "major": major,
                "minor": minor,
            },
            "suppression_ratio": suppressed_alarms / total if total > 0 else 0,
        }
    except Exception as e:
        logger.error(f"Error getting alarm statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
