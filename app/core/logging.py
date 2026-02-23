# Standard library
import logging
import sys
from typing import Any

# Internal
from app.core.config import settings


def configure_logging() -> None:
    """
    Configure application logging.
    - Development: human-readable format, DEBUG level
    - Production/Staging: JSON-structured format, INFO level
    """
    log_level = logging.DEBUG if settings.is_development else logging.INFO

    if settings.is_development:
        # Human-readable format for local development
        fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    else:
        # JSON-structured logging for staging/production
        # In production, pair with a log aggregator (Datadog, GCP Logging, etc.)
        import json

        class JsonFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                log_entry: dict[str, Any] = {
                    "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)
                return json.dumps(log_entry)

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())

    # Apply to root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.is_development else logging.WARNING
    )
