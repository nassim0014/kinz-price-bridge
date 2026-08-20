"""Tests for src/logging_config.py — structured JSON logging."""
from __future__ import annotations

import json
import logging
import io

import pytest

from src.logging_config import JSONFormatter, get_logger


class TestJSONFormatter:
    def test_formats_basic_record_as_json(self):
        """A basic log record is formatted as a JSON object with standard fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="hello world",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["message"] == "hello world"
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert "timestamp" in data

    def test_includes_extra_fields(self):
        """Extra fields passed via extra={...} are merged into the JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="sync_complete",
            args=(),
            exc_info=None,
        )
        record.snapshots_written = 5
        record.products_seen = 5
        output = formatter.format(record)
        data = json.loads(output)
        assert data["snapshots_written"] == 5
        assert data["products_seen"] == 5
        assert data["message"] == "sync_complete"

    def test_includes_exception_info(self):
        """Exception info is included when present."""
        formatter = JSONFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="operation failed",
            args=(),
            exc_info=exc_info,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert "exception" in data
        assert "ValueError" in data["exception"]
        assert "test error" in data["exception"]

    def test_timestamp_is_iso8601(self):
        """The timestamp is ISO-8601 format with timezone."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        # ISO-8601 with timezone: ends with +00:00
        assert data["timestamp"].endswith("+00:00")


class TestGetLogger:
    def test_returns_logger_with_handler(self):
        """get_logger returns a logger with at least one handler."""
        logger = get_logger("test_module")
        assert len(logger.handlers) >= 1
        assert isinstance(logger.handlers[0].formatter, JSONFormatter)

    def test_logger_does_not_propagate(self):
        """The logger does not propagate to the root logger (avoids duplicate output)."""
        logger = get_logger("test_no_propagate")
        assert logger.propagate is False

    def test_logger_emits_json(self, capsys):
        """The logger emits JSON-formatted lines to stdout."""
        logger = get_logger("test_json_output")
        logger.handlers.clear()  # reset to get a fresh handler
        # Re-get to populate handler
        logger = get_logger("test_json_output")
        logger.info("test message", extra={"key": "value"})
        captured = capsys.readouterr()
        # Output should be valid JSON
        line = captured.out.strip()
        data = json.loads(line)
        assert data["message"] == "test message"
        assert data["key"] == "value"
        assert data["level"] == "INFO"
