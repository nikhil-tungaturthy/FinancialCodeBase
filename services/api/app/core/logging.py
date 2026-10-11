"""Structured logging.

structlog renders JSON lines to stdout (``MF_LOG_FORMAT=json``) or a coloured console
layout (``console``). Every record carries ``timestamp``, ``level``, ``event``, ``logger``
and ``service``; request-scoped fields such as ``correlation_id`` are bound through
contextvars so they appear on every line emitted while a request is being handled.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Mapping, MutableMapping
from typing import IO, Any

import structlog
from structlog.typing import EventDict, Processor, WrappedLogger

from app.core.config import SERVICE_NAME, LogFormat

CORRELATION_ID_KEY = "correlation_id"

_NOISY_STDLIB_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine")


def _service_processor(service: str) -> Processor:
    def add_service(_logger: WrappedLogger, _method: str, event_dict: EventDict) -> EventDict:
        event_dict.setdefault("service", service)
        return event_dict

    return add_service


def _order_keys(_logger: WrappedLogger, _method: str, event_dict: EventDict) -> EventDict:
    """Place the stable schema fields first so JSON lines are easy to scan."""
    ordered: dict[str, Any] = {}
    for key in ("timestamp", "level", "event", "logger", "service", CORRELATION_ID_KEY):
        if key in event_dict:
            ordered[key] = event_dict.pop(key)
    ordered.update(event_dict)
    return ordered


def _shared_processors(service: str) -> list[Processor]:
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
        _service_processor(service),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]


def _renderer(fmt: LogFormat) -> Processor:
    if fmt == "console":
        return structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())
    return structlog.processors.JSONRenderer(sort_keys=False)


def configure_logging(
    *,
    level: str = "INFO",
    fmt: LogFormat = "json",
    service: str = SERVICE_NAME,
    stream: IO[str] | None = None,
) -> None:
    """Configure structlog and route the stdlib logging tree through the same renderer."""
    shared = _shared_processors(service)
    json_mode = fmt == "json"
    exception_processors: list[Processor] = (
        [structlog.processors.dict_tracebacks]
        if json_mode
        else [structlog.processors.format_exc_info]
    )
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            *exception_processors,
            _order_keys,
            _renderer(fmt),
        ],
    )
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    for name in _NOISY_STDLIB_LOGGERS:
        noisy = logging.getLogger(name)
        noisy.handlers.clear()
        noisy.propagate = True
    # The request logging middleware emits one line per request; uvicorn's access log
    # would duplicate it.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger bound to ``name`` (usually ``__name__``)."""
    logger: structlog.stdlib.BoundLogger = (
        structlog.get_logger(name) if name else structlog.get_logger()
    )
    return logger


def bind_correlation_id(correlation_id: str) -> Mapping[str, Any]:
    """Bind ``correlation_id`` into the logging context; returns tokens for :func:`unbind`."""
    tokens: Mapping[str, Any] = structlog.contextvars.bind_contextvars(
        **{CORRELATION_ID_KEY: correlation_id}
    )
    return tokens


def bind_log_context(**values: Any) -> Mapping[str, Any]:
    """Bind arbitrary request/job-scoped fields (``payment_ref``, ``batch_ref`` ...)."""
    tokens: Mapping[str, Any] = structlog.contextvars.bind_contextvars(**values)
    return tokens


def unbind(tokens: Mapping[str, Any]) -> None:
    """Restore the context variables captured by a previous ``bind_*`` call."""
    structlog.contextvars.reset_contextvars(**tokens)


def clear_log_context() -> None:
    structlog.contextvars.clear_contextvars()


def current_log_context() -> MutableMapping[str, Any]:
    return dict(structlog.contextvars.get_contextvars())


def get_correlation_id() -> str | None:
    """The correlation id bound to the current context, if any."""
    value = structlog.contextvars.get_contextvars().get(CORRELATION_ID_KEY)
    return str(value) if value is not None else None
