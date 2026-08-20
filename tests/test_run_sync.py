"""Tests for the APScheduler entrypoint (scripts/run_sync.py).

Tests the CLI argument parsing + that run_once() calls sync_latest_prices
and returns its result. Does NOT start the blocking scheduler (that would
hang the test) — run_watch is tested only via its run_once() first call.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest


def test_run_once_returns_summary():
    """run_once() calls sync_latest_prices and returns its result dict."""
    from scripts.run_sync import run_once

    expected = {"snapshots_written": 5, "products_seen": 5}
    with patch("scripts.run_sync.sync_latest_prices", return_value=expected):
        result = run_once()
    assert result == expected


def test_run_once_reraises_on_failure():
    """run_once() re-raises if sync_latest_prices raises."""
    from scripts.run_sync import run_once

    with patch("scripts.run_sync.sync_latest_prices", side_effect=RuntimeError("db down")):
        with pytest.raises(RuntimeError, match="db down"):
            run_once()


def test_main_no_args_runs_once():
    """`run_sync` with no args runs once and returns 0."""
    from scripts.run_sync import main

    with patch("sys.argv", ["run_sync"]), \
         patch("scripts.run_sync.run_once", return_value={"snapshots_written": 0, "products_seen": 0}) as mock_run:
        exit_code = main()
    assert exit_code == 0
    mock_run.assert_called_once()


def test_main_watch_flag_starts_scheduler():
    """`run_sync --watch` calls run_watch instead of run_once."""
    from scripts.run_sync import main

    with patch("sys.argv", ["run_sync", "--watch"]), \
         patch("scripts.run_sync.run_watch") as mock_watch, \
         patch("scripts.run_sync.run_once") as mock_once:
        exit_code = main()
    assert exit_code == 0
    mock_watch.assert_called_once()
    mock_once.assert_not_called()


def test_main_watch_with_custom_interval():
    """`run_sync --watch --interval 15` passes the interval to run_watch."""
    from scripts.run_sync import main

    with patch("sys.argv", ["run_sync", "--watch", "--interval", "15"]), \
         patch("scripts.run_sync.run_watch") as mock_watch:
        exit_code = main()
    assert exit_code == 0
    # run_watch should be called with interval_minutes=15
    args, kwargs = mock_watch.call_args
    assert kwargs.get("interval_minutes") == 15 or (args and args[0] == 15)


def test_main_returns_1_on_exception():
    """`run_sync` returns 1 if run_once raises."""
    from scripts.run_sync import main

    with patch("sys.argv", ["run_sync"]), \
         patch("scripts.run_sync.run_once", side_effect=RuntimeError("boom")):
        exit_code = main()
    assert exit_code == 1
