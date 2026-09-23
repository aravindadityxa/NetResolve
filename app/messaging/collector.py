"""Event collection service."""

import threading
import time
from typing import Optional, List
from datetime import datetime

from app.core.logging import logger
from app.core.config import settings
from app.messaging.kafka import KafkaEventProducer
from app.services.event_service import EventService
from app.simulator import get_simulator
from app.schemas.event import NetworkEventSchema
from app.core.database import SessionLocal


class EventCollector:
    """Collects events from various sources and publishes to Kafka."""

    def __init__(self):
        """Initialize event collector."""
        self.producer = KafkaEventProducer()
        self.is_running = False
        self.collection_threads: List[threading.Thread] = []
        self.event_count = 0
        self._lock = threading.Lock()

    def start(self):
        """Start the event collector."""
        self.is_running = True
        logger.info("Event collector started")

        # Start simulator thread
        if settings.simulator_enabled:
            sim_thread = threading.Thread(
                target=self._collect_simulator_events,
                daemon=True,
            )
            sim_thread.start()
            self.collection_threads.append(sim_thread)
            logger.info("Simulator event collector started")

    def stop(self):
        """Stop the event collector."""
        self.is_running = False
        self.producer.close()
        logger.info(f"Event collector stopped (collected {self.event_count} events)")

    def _collect_simulator_events(self):
        """Collect events from simulator."""
        simulator = get_simulator()
        db = SessionLocal()

        try:
            last_event_count = 0

            while self.is_running:
                try:
                    current_event_count = simulator.get_event_count()

                    # New events available
                    if current_event_count > last_event_count:
                        new_events = simulator.get_event_history(
                            limit=current_event_count - last_event_count
                        )

                        for sim_event in new_events:
                            try:
                                # Create schema from simulator event
                                event_schema = NetworkEventSchema(
                                    event_id=sim_event["event_id"],
                                    timestamp=datetime.fromisoformat(
                                        sim_event["timestamp"]
                                    ),
                                    source=sim_event["source"],
                                    device_id=sim_event["device_id"],
                                    device_hostname=sim_event["device_hostname"],
                                    event_type=sim_event["event_type"],
                                    interface_id=sim_event.get("interface_id"),
                                    severity=sim_event["severity"],
                                    message=sim_event["message"],
                                )

                                # Save to database
                                db_event = EventService.create_event(db, event_schema)

                                # Publish to Kafka
                                event_dict = {
                                    "event_id": event_schema.event_id,
                                    "timestamp": event_schema.timestamp.isoformat(),
                                    "source": event_schema.source,
                                    "device_id": event_schema.device_id,
                                    "device_hostname": event_schema.device_hostname,
                                    "event_type": event_schema.event_type,
                                    "interface_id": event_schema.interface_id,
                                    "severity": event_schema.severity,
                                    "message": event_schema.message,
                                    "raw_data": event_schema.raw_data,
                                }

                                self.producer.send_event(
                                    event_dict,
                                    topic=settings.kafka_event_topic,
                                )

                                with self._lock:
                                    self.event_count += 1

                                logger.debug(
                                    f"Event collected and published: "
                                    f"{event_schema.device_hostname} - {event_schema.event_type}"
                                )

                            except Exception as e:
                                logger.error(f"Error processing simulator event: {e}")

                        last_event_count = current_event_count

                    time.sleep(0.5)  # Poll interval

                except Exception as e:
                    logger.error(f"Error in simulator collector: {e}")
                    time.sleep(1)

        finally:
            db.close()

    def get_event_count(self) -> int:
        """Get total events collected."""
        with self._lock:
            return self.event_count


# Global collector instance
_collector = None


def get_collector() -> EventCollector:
    """Get or create global collector instance."""
    global _collector
    if _collector is None:
        _collector = EventCollector()
    return _collector
