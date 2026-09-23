"""Health check endpoints."""

from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.core.logging import logger
from app.core.database import SessionLocal
from app.services.background_service import get_background_manager

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "netresolve-api",
        "version": "1.0.0",
    }


@router.get("/status")
async def system_status():
    """Get system status."""
    try:
        # Check database
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        db_status = "ok"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "error"

    # Check background services
    try:
        manager = get_background_manager()
        services_status = manager.get_status()
    except Exception as e:
        logger.error(f"Background services status check failed: {e}")
        services_status = {}

    return {
        "status": "operational" if db_status == "ok" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
        "services": services_status,
        "environment": "production",
    }
