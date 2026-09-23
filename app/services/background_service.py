"""Background service manager for event collection and processing."""

import threading
from typing import List

from app.core.logging import logger
from app.core.config import settings
from app.messaging.collector import get_collector
from app.messaging.alarm_ingester import get_ingester


class BackgroundServiceManager:
    """Manages background services like event collection."""

    def __init__(self):
        """Initialize background service manager."""
        self.services: List[str] = []
        self.collector = None
        self.ingester = None
        self._lock = threading.Lock()

    def start(self):
        """Start all background services."""
        with self._lock:
            logger.info("Starting background services...")

            # Start event collector
            if settings.simulator_enabled:
                self.collector = get_collector()
                self.collector.start()
                self.services.append("collector")
                logger.info("✓ Event collector started")

            # Start alarm ingester
            self.ingester = get_ingester()
            self.ingester.start()
            self.services.append("ingester")
            logger.info("✓ Alarm ingester started")

            logger.info(f"Background services started: {', '.join(self.services)}")

    def stop(self):
        """Stop all background services."""
        with self._lock:
            logger.info("Stopping background services...")

            if self.collector:
                self.collector.stop()
                logger.info("✓ Event collector stopped")

            if self.ingester:
                self.ingester.stop()
                logger.info("✓ Alarm ingester stopped")

            self.services.clear()
            logger.info("Background services stopped")

    def get_status(self) -> dict:
        """Get status of all services."""
        return {
            "running": len(self.services) > 0,
            "services": self.services,
            "collector": {
                "running": self.collector is not None and self.collector.is_running,
                "event_count": self.collector.get_event_count() if self.collector else 0,
            } if self.collector else None,
            "ingester": {
                "running": self.ingester is not None and self.ingester.is_running,
                "alarm_count": self.ingester.alarm_count if self.ingester else 0,
            } if self.ingester else None,
        }


# Global instance
_manager = None


def get_background_manager() -> BackgroundServiceManager:
    """Get or create global background service manager."""
    global _manager
    if _manager is None:
        _manager = BackgroundServiceManager()
    return _manager
