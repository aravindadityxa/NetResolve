#!/usr/bin/env python3
"""Database migration utility."""

import sys
import subprocess
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.logging import logger


def run_upgrade():
    """Run database upgrade migrations."""
    logger.info("Running database migrations (upgrade)...")
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info(result.stdout)
        logger.info("✓ Database upgrade complete")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Migration failed: {e.stderr}")
        return False
    except FileNotFoundError:
        logger.error("Alembic not found. Install with: pip install alembic")
        return False


def run_downgrade(revision: str = "-1"):
    """Run database downgrade migrations."""
    logger.info(f"Running database migrations (downgrade to {revision})...")
    try:
        result = subprocess.run(
            ["alembic", "downgrade", revision],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info(result.stdout)
        logger.info("✓ Database downgrade complete")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Migration failed: {e.stderr}")
        return False


def show_current():
    """Show current database version."""
    logger.info("Checking current database version...")
    try:
        result = subprocess.run(
            ["alembic", "current"],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get current version: {e.stderr}")
        return False


def show_history():
    """Show migration history."""
    logger.info("Migration history:")
    try:
        result = subprocess.run(
            ["alembic", "history"],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get history: {e.stderr}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/migrate.py <command>")
        print("")
        print("Commands:")
        print("  upgrade    - Apply migrations")
        print("  downgrade  - Downgrade migrations")
        print("  current    - Show current version")
        print("  history    - Show migration history")
        sys.exit(1)

    command = sys.argv[1]

    if command == "upgrade":
        success = run_upgrade()
    elif command == "downgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "-1"
        success = run_downgrade(revision)
    elif command == "current":
        success = show_current()
    elif command == "history":
        success = show_history()
    else:
        logger.error(f"Unknown command: {command}")
        success = False

    sys.exit(0 if success else 1)
