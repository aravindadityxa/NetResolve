"""Main application entry point."""

from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import logger
from app.core.database import init_db
from app.services.background_service import get_background_manager

# Import API routers
from app.api import health, devices, alarms, incidents, topology, simulator, correlation, metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    logger.info(f"Starting NetResolve in {settings.environment} environment")
    try:
        init_db()
        logger.info("✓ Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # Start background services
    try:
        manager = get_background_manager()
        manager.start()
        logger.info("✓ Background services started")
    except Exception as e:
        logger.error(f"Failed to start background services: {e}")
        # Don't fail startup, but log the error
        pass

    yield

    # Shutdown
    logger.info("Shutting down NetResolve")
    try:
        manager = get_background_manager()
        manager.stop()
        logger.info("✓ Background services stopped")
    except Exception as e:
        logger.error(f"Error stopping background services: {e}")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="NetResolve",
        description="Automated Network Root Cause Analysis & Alarm Suppression Platform",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Include routers
    app.include_router(health.router, prefix="/api")
    app.include_router(devices.router, prefix="/api")
    app.include_router(alarms.router, prefix="/api")
    app.include_router(incidents.router, prefix="/api")
    app.include_router(topology.router, prefix="/api")
    app.include_router(simulator.router, prefix="/api")
    app.include_router(correlation.router, prefix="/api")
    app.include_router(metrics.router, prefix="/api")

    logger.info("FastAPI application created")
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )
