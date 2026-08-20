"""Structured JSON logging for kinz-price-bridge.

Emits one JSON object per log line so Docker/k8s log aggregation
(Loki, Elasticsearch, CloudWatch) can parse fields without regex.

Usage:
    from src.logging_config import get_logger
    log = get_logger(__name__)
    log.info("sync_started", extra={"interval_minutes": 30})
    log.info("sync_complete", extra={"snapshots_written": 5, "products_seen": 5})

The structured fields appear alongside the standard fields (timestamp,
level, logger name, message) in the JSON output.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from src.config import LOG_LEVEL


class JSONFormatter(logging.Formatter):
    """Format log records as JSON lines.

    Standard fields: timestamp, level, logger, message.
    Extra fields passed via `extra={...}` are merged in.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Base fields
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Merge in any extra fields (passed via extra={...})
        # The logging module stores extras as attributes on the record;
        # we exclude the standard ones.
        standard_attrs = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "asctime", "taskName",
        }
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                entry[key] = value

        # Include exception info if present
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(entry, default=str)


def get_logger(name: str) -> logging.Logger:
    """Get a logger configured for JSON output.

    Call once per module at import time:
        log = get_logger(__name__)
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
        # Don't propagate to root logger (avoids duplicate plain-text output)
        logger.propagate = False
    return logger
