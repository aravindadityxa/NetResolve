"""Apache Kafka producer and consumer utilities."""

import json
from typing import Optional, Dict, Any, Callable
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import logging

from app.core.config import settings
from app.core.logging import logger


class KafkaEventProducer:
    """Kafka event producer for publishing events."""

    def __init__(self, topic: str = None):
        """Initialize Kafka producer."""
        self.topic = topic or settings.kafka_event_topic
        self.producer = None
        self._connect()

    def _connect(self):
        """Connect to Kafka."""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                retries=3,
                acks="all",
            )
            logger.info(f"Kafka producer connected to {settings.kafka_bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise

    def send_event(self, event: Dict[str, Any], topic: str = None) -> bool:
        """
        Send an event to Kafka.

        Args:
            event: Event dictionary
            topic: Optional topic override

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.producer:
            logger.error("Producer not connected")
            return False

        target_topic = topic or self.topic

        try:
            future = self.producer.send(target_topic, value=event)
            record_metadata = future.get(timeout=10)
            logger.debug(
                f"Event sent to {record_metadata.topic}:"
                f"{record_metadata.partition}@{record_metadata.offset}"
            )
            return True
        except KafkaError as e:
            logger.error(f"Failed to send event to Kafka: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending event: {e}")
            return False

    def send_batch(self, events: list, topic: str = None) -> int:
        """
        Send multiple events to Kafka.

        Args:
            events: List of event dictionaries
            topic: Optional topic override

        Returns:
            Number of events sent successfully
        """
        if not self.producer:
            return 0

        sent_count = 0
        for event in events:
            if self.send_event(event, topic):
                sent_count += 1

        return sent_count

    def close(self):
        """Close producer connection."""
        if self.producer:
            self.producer.close()
            logger.info("Kafka producer closed")


class KafkaEventConsumer:
    """Kafka event consumer for receiving events."""

    def __init__(
        self,
        topic: str,
        group_id: str,
        auto_offset_reset: str = "earliest",
    ):
        """
        Initialize Kafka consumer.

        Args:
            topic: Topic to consume from
            group_id: Consumer group ID
            auto_offset_reset: Where to start reading ('earliest' or 'latest')
        """
        self.topic = topic
        self.group_id = group_id
        self.consumer = None
        self._connect(auto_offset_reset)

    def _connect(self, auto_offset_reset: str):
        """Connect to Kafka."""
        try:
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=settings.kafka_bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset=auto_offset_reset,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                session_timeout_ms=10000,
                heartbeat_interval_ms=3000,
            )
            logger.info(
                f"Kafka consumer connected to {settings.kafka_bootstrap_servers} "
                f"(topic={self.topic}, group={self.group_id})"
            )
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise

    def consume(
        self,
        callback: Callable[[Dict[str, Any]], None],
        timeout_ms: int = 1000,
    ):
        """
        Consume events from Kafka and process with callback.

        Args:
            callback: Function to call for each event
            timeout_ms: Poll timeout in milliseconds

        Yields:
            Processed events
        """
        if not self.consumer:
            logger.error("Consumer not connected")
            return

        try:
            for message in self.consumer:
                try:
                    event = message.value
                    callback(event)
                    yield event
                except Exception as e:
                    logger.error(f"Error processing event: {e}")
                    continue
        except KeyboardInterrupt:
            logger.info("Consumer interrupted")
        except Exception as e:
            logger.error(f"Consumer error: {e}")
        finally:
            self.close()

    def consume_batch(
        self,
        callback: Callable[[list], None],
        batch_size: int = 10,
        timeout_ms: int = 5000,
    ):
        """
        Consume events in batches.

        Args:
            callback: Function to call with batch of events
            batch_size: Number of events per batch
            timeout_ms: Poll timeout in milliseconds
        """
        if not self.consumer:
            logger.error("Consumer not connected")
            return

        batch = []
        try:
            for message in self.consumer:
                try:
                    event = message.value
                    batch.append(event)

                    if len(batch) >= batch_size:
                        callback(batch)
                        batch = []
                except Exception as e:
                    logger.error(f"Error processing event: {e}")
                    continue

            # Process remaining events
            if batch:
                callback(batch)
        except KeyboardInterrupt:
            logger.info("Batch consumer interrupted")
        except Exception as e:
            logger.error(f"Batch consumer error: {e}")
        finally:
            self.close()

    def close(self):
        """Close consumer connection."""
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")


def create_producer(topic: str = None) -> KafkaEventProducer:
    """Factory function to create a producer."""
    return KafkaEventProducer(topic)


def create_consumer(
    topic: str,
    group_id: str,
    auto_offset_reset: str = "earliest",
) -> KafkaEventConsumer:
    """Factory function to create a consumer."""
    return KafkaEventConsumer(topic, group_id, auto_offset_reset)
