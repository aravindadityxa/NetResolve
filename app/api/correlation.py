"""Correlation and RCA endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any

from app.core.logging import logger
from app.core.database import SessionLocal
from app.models.alarm import Alarm
from app.rca.analyzer import RCAAnalyzer

router = APIRouter(tags=["Correlation & RCA"])


@router.get("/correlation/groups")
async def list_correlation_groups(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List alarm correlation groups."""
    try:
        db = SessionLocal()

        # Get distinct correlation IDs
        groups = (
            db.query(Alarm.correlation_id)
            .filter(Alarm.correlation_id.isnot(None))
            .distinct()
            .offset(offset)
            .limit(limit)
            .all()
        )

        group_info = []
        for (group_id,) in groups:
            alarms = db.query(Alarm).filter(Alarm.correlation_id == group_id).all()
            severity_counts = {}
            for a in alarms:
                severity_counts[a.severity] = severity_counts.get(a.severity, 0) + 1

            group_info.append({
                "correlation_id": group_id,
                "alarm_count": len(alarms),
                "severity_distribution": severity_counts,
                "first_alarm_time": min([a.created_at for a in alarms]).isoformat(),
                "last_alarm_time": max([a.created_at for a in alarms]).isoformat(),
            })

        db.close()
        return group_info
    except Exception as e:
        logger.error(f"Error listing correlation groups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/correlation/{correlation_id}")
async def get_correlation_group(correlation_id: str):
    """Get correlation group details."""
    try:
        db = SessionLocal()

        alarms = (
            db.query(Alarm)
            .filter(Alarm.correlation_id == correlation_id)
            .order_by(Alarm.created_at)
            .all()
        )

        if not alarms:
            db.close()
            raise HTTPException(status_code=404, detail="Correlation group not found")

        db.close()

        return {
            "correlation_id": correlation_id,
            "alarm_count": len(alarms),
            "alarms": [
                {
                    "id": a.id,
                    "device_id": a.device_id,
                    "alarm_type": a.alarm_type,
                    "severity": a.severity,
                    "status": a.status,
                    "message": a.message,
                    "created_at": a.created_at.isoformat(),
                }
                for a in alarms
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting correlation group: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rca/{correlation_id}/analyze")
async def analyze_correlation_group(correlation_id: str) -> Dict[str, Any]:
    """Analyze correlation group for root cause."""
    try:
        db = SessionLocal()

        alarms = db.query(Alarm).filter(Alarm.correlation_id == correlation_id).all()

        if not alarms:
            db.close()
            raise HTTPException(status_code=404, detail="Correlation group not found")

        # Run RCA analysis
        analyzer = RCAAnalyzer(db)
        rca_result = analyzer.analyze_correlation_group(correlation_id)

        db.close()

        return {
            "correlation_id": correlation_id,
            "alarm_count": len(alarms),
            "root_cause_id": rca_result.get("root_cause_alarm_id"),
            "root_cause_device": rca_result.get("root_cause_device_hostname"),
            "root_cause_type": rca_result.get("root_cause_type"),
            "confidence": rca_result.get("confidence"),
            "affected_devices": rca_result.get("affected_devices"),
            "blast_radius": rca_result.get("blast_radius"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing group: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rca/{correlation_id}/reasoning")
async def get_rca_reasoning(correlation_id: str):
    """Get RCA reasoning for a correlation group."""
    try:
        db = SessionLocal()

        alarms = db.query(Alarm).filter(Alarm.correlation_id == correlation_id).all()

        if not alarms:
            db.close()
            raise HTTPException(status_code=404, detail="Correlation group not found")

        analyzer = RCAAnalyzer(db)
        rca_result = analyzer.analyze_correlation_group(correlation_id)

        db.close()

        return {
            "correlation_id": correlation_id,
            "root_cause_id": rca_result.get("root_cause_alarm_id"),
            "root_cause_device": rca_result.get("root_cause_device_hostname"),
            "reasoning": rca_result.get("reasoning"),
            "confidence": rca_result.get("confidence"),
            "confidence_factors": rca_result.get("confidence_factors"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting RCA reasoning: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rca/{correlation_id}/remediation")
async def get_remediation_suggestions(correlation_id: str):
    """Get remediation suggestions for root cause."""
    try:
        db = SessionLocal()

        alarms = db.query(Alarm).filter(Alarm.correlation_id == correlation_id).all()

        if not alarms:
            db.close()
            raise HTTPException(status_code=404, detail="Correlation group not found")

        # Get root cause alarm
        analyzer = RCAAnalyzer(db)
        rca_result = analyzer.analyze_correlation_group(correlation_id)
        root_cause_alarm = (
            db.query(Alarm).filter(Alarm.id == rca_result.get("root_cause_alarm_id")).first()
        )

        db.close()

        # Generate remediation based on alarm type
        remediation = []
        if root_cause_alarm:
            if "interface" in root_cause_alarm.alarm_type.lower():
                remediation = [
                    "Check interface hardware status",
                    "Verify interface configuration",
                    "Restart interface",
                    "Check interface optics (if SFP)",
                    "Verify fiber connections",
                ]
            elif "device" in root_cause_alarm.alarm_type.lower():
                remediation = [
                    "Verify device connectivity",
                    "Check device power supply",
                    "Restart device",
                    "Check device logs",
                    "Verify device configuration",
                ]
            elif "latency" in root_cause_alarm.alarm_type.lower():
                remediation = [
                    "Check link bandwidth utilization",
                    "Verify QoS configuration",
                    "Check for routing loops",
                    "Look for unusual traffic patterns",
                    "Consider link upgrade",
                ]
            elif "packet" in root_cause_alarm.alarm_type.lower():
                remediation = [
                    "Check link quality metrics",
                    "Verify interface errors",
                    "Check for congestion",
                    "Review routing table",
                    "Consider link upgrade",
                ]

        return {
            "correlation_id": correlation_id,
            "root_cause_type": root_cause_alarm.alarm_type if root_cause_alarm else "unknown",
            "recommended_actions": remediation or [
                "Investigate root cause alarm",
                "Check related device logs",
                "Verify network topology",
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting remediation suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
