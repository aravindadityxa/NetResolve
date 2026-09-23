"""Alarm ingestion service - consumes events and creates alarms."""

import threading
import time
from typing import Dict, Any, List
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.core.config import settings
from app.core.database import SessionLocal
from app.messaging.kafka import KafkaEventConsumer, create_producer
from app.messaging.normalizer import EventNormalizer
from app.services.alarm_service import AlarmService
from app.services.event_service import EventService


class AlarmIngester:
    """Consumes events, normalizes to alarms, and publishes to alarm topic."""

    def __init__(self):
        """Initialize alarm ingester."""
        self.is_running = False
        self.consumer = None
        self.producer = create_producer(settings.kafka_alarm_topic)
        self.alarm_count = 0
        self._lock = threading.Lock()

    def start(self):
        """Start the alarm ingester."""
        self.is_running = True
        logger.info("Alarm ingester started")

        # Start consumer thread
        thread = threading.Thread(
            target=self._ingest_events,
            daemon=True,
        )
        thread.start()

    def stop(self):
        """Stop the alarm ingester."""
        self.is_running = False
        if self.consumer:
            self.consumer.close()
        self.producer.close()
        logger.info(f"Alarm ingester stopped (created {self.alarm_count} alarms)")

    def _ingest_events(self):
        """Ingest events and create alarms."""
        try:
            self.consumer = KafkaEventConsumer(
                topic=settings.kafka_event_topic,
                group_id="alarm-ingester",
                auto_offset_reset="latest",
            )

            # Process events from Kafka
            db = SessionLocal()
            try:
                for event in self.consumer.consume(self._process_event):
                    pass
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error in alarm ingester: {e}")
            time.sleep(5)
            # Restart
            if self.is_running:
                self._ingest_events()

    def _process_event(self, event: Dict[str, Any]):
        """Process a single event."""
        try:
            db = SessionLocal()

            try:
                # Check if event already processed
                existing_event = EventService.get_event_by_event_id(db, event["event_id"])
                if existing_event:
                    logger.debug(f"Event {event['event_id']} already processed")
                    return

                # Normalize event to alarm
                alarm_schema = EventNormalizer.normalize(event)
                if not alarm_schema:
                    logger.warning(f"Failed to normalize event {event.get('event_id')}")
                    return

                # Check for duplicate alarm (same device, same type, within 5 minutes)
                existing_alarm = AlarmService.deduplicate_alarm(
                    db,
                    device_id=alarm_schema.device_id,
                    alarm_type=alarm_schema.alarm_type.value,
                )

                if existing_alarm:
                    logger.info(
                        f"Deduplicated alarm {alarm_schema.alarm_type.value} "
                        f"on {alarm_schema.device_hostname}"
                    )
                    alarm = existing_alarm
                else:
                    # Create new alarm
                    alarm = AlarmService.create_alarm(db, alarm_schema)

                with self._lock:
                    self.alarm_count += 1

                # Publish alarm to Kafka for correlation
                alarm_dict = {
                    "id": alarm.id,
                    "event_id": alarm.event_id,
                    "timestamp": alarm.timestamp.isoformat(),
                    "device_id": alarm.device_id,
                    "device_hostname": alarm.device_hostname,
                    "interface_id": alarm.interface_id,
                    "alarm_type": alarm.alarm_type.value,
                    "severity": alarm.severity.value,
                    "status": alarm.status.value,
                    "message": alarm.message,
                    "source": alarm.source,
                    "occurrence_count": alarm.occurrence_count,
                }

                self.producer.send_event(alarm_dict)

                logger.debug(
                    f"Created and published alarm {alarm.id}: "
                    f"{alarm.alarm_type.value} on {alarm.device_hostname}"
                )

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error processing event: {e}")


# Global ingester instance
_ingester = None


def get_ingester() -> AlarmIngester:
    """Get or create global ingester instance."""
    global _ingester
    if _ingester is None:
        _ingester = AlarmIngester()
    return _ingester
