"""structlog JSON output carries the §10 schema fields."""

from __future__ import annotations

import io
import json
import logging

from app.core.logging import (
    bind_correlation_id,
    clear_log_context,
    configure_logging,
    get_correlation_id,
    get_logger,
    unbind,
)


def test_json_lines_carry_schema_fields_and_bound_correlation_id() -> None:
    stream = io.StringIO()
    configure_logging(level="INFO", fmt="json", service="meridian-api", stream=stream)
    try:
        tokens = bind_correlation_id("corr-log-1")
        try:
            get_logger("meridian.test").info(
                "http.request", method="GET", path="/health", status_code=200, duration_ms=1.5
            )
            logging.getLogger("uvicorn.error").warning("stdlib line %s", "routed")
        finally:
            unbind(tokens)
        assert get_correlation_id() is None
    finally:
        configure_logging(level="WARNING", fmt="console", service="meridian-api")

    lines = [json.loads(line) for line in stream.getvalue().splitlines()]
    structured = next(line for line in lines if line["event"] == "http.request")
    assert list(structured)[:6] == [
        "timestamp", "level", "event", "logger", "service", "correlation_id",
    ]  # fmt: skip
    assert structured["level"] == "info"
    assert structured["service"] == "meridian-api"
    assert structured["correlation_id"] == "corr-log-1"
    assert structured["logger"] == "meridian.test"
    assert structured["status_code"] == 200
    assert structured["timestamp"].endswith("Z")

    foreign = next(line for line in lines if line["event"] == "stdlib line routed")
    assert foreign["logger"] == "uvicorn.error"
    assert foreign["service"] == "meridian-api"
    assert foreign["level"] == "warning"


def test_clear_log_context() -> None:
    bind_correlation_id("corr-x")
    clear_log_context()
    assert get_correlation_id() is None
