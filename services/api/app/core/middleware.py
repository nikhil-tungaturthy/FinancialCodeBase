"""ASGI middleware: correlation ids and request logging.

Both middlewares are plain ASGI callables (not ``BaseHTTPMiddleware``) so that the
contextvars they bind are visible to the route handlers and exception handlers that run
inside them.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import CORRELATION_HEADER
from app.core.ids import new_correlation_id
from app.core.logging import bind_correlation_id, get_logger, unbind

log = get_logger("meridian.http")

_QUIET_PATHS = frozenset({"/health", "/ready", "/api/v1/health", "/api/v1/ready"})


class CorrelationIdMiddleware:
    """Honour an inbound ``X-Correlation-ID`` (or mint one) and echo it on the response."""

    def __init__(self, app: ASGIApp, header_name: str = CORRELATION_HEADER) -> None:
        self.app = app
        self.header_name = header_name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        inbound = Headers(scope=scope).get(self.header_name, "").strip()
        correlation_id = inbound[:128] if inbound else new_correlation_id()
        state: dict[str, Any] = scope.setdefault("state", {})
        state["correlation_id"] = correlation_id
        tokens: Mapping[str, Any] = bind_correlation_id(correlation_id)

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                if self.header_name not in headers:
                    headers.append(self.header_name, correlation_id)
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            unbind(tokens)


class RequestLoggingMiddleware:
    """Emit one structured ``http.request`` line per request with timing and status."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method: str = scope.get("method", "")
        path: str = scope.get("path", "")
        started = time.perf_counter()
        status_code: int | None = None

        async def send_and_capture(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, send_and_capture)
        except Exception:
            status_code = 500
            raise
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            fields = {
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
            }
            if path in _QUIET_PATHS:
                log.debug("http.request", **fields)
            elif status_code is not None and status_code >= 500:
                log.error("http.request", **fields)
            else:
                log.info("http.request", **fields)
