"""Domain error hierarchy and RFC 9457 problem-details handlers.

Services raise :class:`DomainError` subclasses; the handlers registered by
:func:`register_exception_handlers` turn them (and framework errors) into
``application/problem+json`` responses that always carry the request's correlation id,
both in the body and in the ``X-Correlation-ID`` header.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from http import HTTPStatus
from typing import Any, ClassVar

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_correlation_id, get_logger

PROBLEM_MEDIA_TYPE = "application/problem+json"
PROBLEM_TYPE_PREFIX = "urn:meridian-flow:problem:"
CORRELATION_HEADER = "X-Correlation-ID"

log = get_logger(__name__)


class DomainError(Exception):
    """Base class for errors that map to a specific HTTP problem response."""

    status_code: ClassVar[int] = 400
    title: ClassVar[str] = "Request could not be processed"
    problem_type: ClassVar[str] = "domain-error"

    def __init__(
        self,
        detail: str,
        *,
        errors: Sequence[Mapping[str, Any]] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.errors: list[dict[str, Any]] | None = (
            [dict(error) for error in errors] if errors is not None else None
        )
        self.context: dict[str, Any] = dict(context or {})

    def __str__(self) -> str:
        return self.detail


class NotFoundError(DomainError):
    status_code = 404
    title = "Resource not found"
    problem_type = "not-found"

    @classmethod
    def for_entity(cls, entity_type: str, ref: str) -> NotFoundError:
        return cls(
            f"{entity_type} {ref} was not found",
            context={"entity_type": entity_type, "entity_ref": ref},
        )


class ConflictError(DomainError):
    status_code = 409
    title = "Conflict with current state"
    problem_type = "conflict"


class InvalidTransitionError(ConflictError):
    """Raised when a lifecycle transition is not allowed from the current status."""

    title = "Invalid state transition"
    problem_type = "invalid-transition"

    def __init__(
        self,
        from_status: object,
        to_status: object,
        *,
        entity: str = "payment",
        entity_ref: str | None = None,
    ) -> None:
        self.from_status = _status_name(from_status)
        self.to_status = _status_name(to_status)
        self.entity = entity
        self.entity_ref = entity_ref
        subject = f"{entity} {entity_ref}" if entity_ref else entity
        super().__init__(
            f"Cannot transition {subject} from {self.from_status} to {self.to_status}",
            context={
                "entity": entity,
                "entity_ref": entity_ref,
                "from_status": self.from_status,
                "to_status": self.to_status,
            },
        )


class AuthenticationError(DomainError):
    status_code = 401
    title = "Unknown demo identity"
    problem_type = "unauthenticated"


class AuthorizationError(DomainError):
    status_code = 403
    title = "Operation not permitted for this role"
    problem_type = "forbidden"


class ValidationFailed(DomainError):  # noqa: N818 - name is part of the service contract
    status_code = 422
    title = "Validation failed"
    problem_type = "validation-failed"


def _status_name(value: object) -> str:
    name = getattr(value, "value", value)
    return str(name)


def correlation_id_for(request: Request) -> str | None:
    """The correlation id assigned to ``request`` by the middleware (or bound in logs)."""
    state_value = getattr(request.state, "correlation_id", None)
    if isinstance(state_value, str) and state_value:
        return state_value
    return get_correlation_id()


def problem_response(
    request: Request,
    *,
    status: int,
    title: str,
    detail: str | None,
    problem_type: str,
    errors: Sequence[Mapping[str, Any]] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> JSONResponse:
    """Build a problem+json response with the correlation id in body and header."""
    correlation_id = correlation_id_for(request)
    body: dict[str, Any] = {
        "type": f"{PROBLEM_TYPE_PREFIX}{problem_type}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": str(request.url.path),
        "correlation_id": correlation_id,
    }
    if errors is not None:
        body["errors"] = [dict(error) for error in errors]
    if extra:
        body.update(extra)
    headers = {CORRELATION_HEADER: correlation_id} if correlation_id else None
    return JSONResponse(
        status_code=status,
        content=body,
        media_type=PROBLEM_MEDIA_TYPE,
        headers=headers,
    )


def _sanitise_validation_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for error in exc.errors():
        cleaned.append(
            {
                "loc": [str(part) if not isinstance(part, int) else part for part in error["loc"]],
                "msg": str(error.get("msg", "")),
                "type": str(error.get("type", "")),
            }
        )
    return cleaned


async def domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    if exc.status_code >= 500:
        log.error("domain_error", problem_type=exc.problem_type, detail=exc.detail)
    else:
        log.info("domain_error", problem_type=exc.problem_type, detail=exc.detail, **exc.context)
    return problem_response(
        request,
        status=exc.status_code,
        title=exc.title,
        detail=exc.detail,
        problem_type=exc.problem_type,
        errors=exc.errors,
        extra=exc.context or None,
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    status = exc.status_code
    try:
        phrase = HTTPStatus(status).phrase
    except ValueError:
        phrase = "HTTP error"
    detail = exc.detail if isinstance(exc.detail, str) else phrase
    response = problem_response(
        request,
        status=status,
        title=phrase,
        detail=detail,
        problem_type=f"http-{status}",
    )
    if exc.headers:
        for key, value in exc.headers.items():
            response.headers[key] = value
    return response


async def request_validation_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    return problem_response(
        request,
        status=422,
        title="Request validation failed",
        detail="One or more request fields are invalid",
        problem_type="request-validation",
        errors=_sanitise_validation_errors(exc),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled_exception", error_type=type(exc).__name__)
    return problem_response(
        request,
        status=500,
        title="Internal server error",
        detail="An unexpected error occurred; quote the correlation id when reporting it",
        problem_type="internal-error",
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
