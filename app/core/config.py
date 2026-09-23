"""Application configuration."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql://netresolve:netresolve@localhost:5432/netresolve"
    database_echo: bool = False

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_alarm_topic: str = "netresolve.alarms"
    kafka_event_topic: str = "netresolve.events"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True

    # Simulator
    simulator_enabled: bool = True
    simulator_event_interval: int = 5  # seconds

    # Logging
    log_level: str = "INFO"

    # Environment
    environment: str = "development"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
