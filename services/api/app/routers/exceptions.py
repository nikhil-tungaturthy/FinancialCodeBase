"""Exception queue and workbench (``/api/v1/exceptions``)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import CurrentUser, require_role
from app.auth.identity import find_user
from app.core.errors import NotFoundError
from app.db.session import SessionDep
from app.models.enums import ExceptionSeverity, ExceptionStatus, Role
from app.models.users import User
from app.schemas.common import Page, SortOrder
from app.schemas.exceptions import (
    AssignRequest,
    ExceptionActionRequest,
    ExceptionActionResponse,
    ExceptionDetail,
    ExceptionQueueItem,
    ExceptionSortField,
    ExceptionSummaryResponse,
    NoteRequest,
)
from app.services import queries
from app.services.workflow import (
    add_note,
    assign_exception,
    perform_action,
    require_exception,
)

router = APIRouter(prefix="/api/v1/exceptions", tags=["exceptions"])


@router.get("", response_model=Page[ExceptionQueueItem])
def list_exceptions(
    session: SessionDep,
    _user: CurrentUser,
    status: Annotated[list[ExceptionStatus] | None, Query()] = None,
    severity: Annotated[list[ExceptionSeverity] | None, Query()] = None,
    assigned_to: str | None = None,
    queue: str | None = None,
    search: str | None = None,
    sort: ExceptionSortField = "due_by",
    order: SortOrder = "asc",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
) -> Page[ExceptionQueueItem]:
    return queries.list_exceptions(
        session,
        statuses=status,
        severities=severity,
        assigned_to=assigned_to,
        queue=queue,
        search=search,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )


@router.get("/summary", response_model=ExceptionSummaryResponse)
def summary(session: SessionDep, _user: CurrentUser) -> ExceptionSummaryResponse:
    return queries.exception_summary(session)


@router.get("/{exception_ref}", response_model=ExceptionDetail)
def get_exception(exception_ref: str, session: SessionDep, user: CurrentUser) -> ExceptionDetail:
    return queries.get_exception(session, exception_ref, user)


@router.post("/{exception_ref}/assign", response_model=ExceptionDetail)
def assign(
    exception_ref: str,
    body: AssignRequest,
    session: SessionDep,
    user: Annotated[User, Depends(require_role(Role.ANALYST))],
) -> ExceptionDetail:
    item = require_exception(session, exception_ref)
    assignee = find_user(session, body.assignee_username)
    if assignee is None:
        raise NotFoundError.for_entity("user", body.assignee_username)
    assign_exception(session, item, user, assignee, body.note)
    session.flush()
    return queries.get_exception(session, exception_ref, user)


@router.post("/{exception_ref}/notes", response_model=ExceptionDetail)
def notes(
    exception_ref: str,
    body: NoteRequest,
    session: SessionDep,
    user: Annotated[User, Depends(require_role(Role.ANALYST))],
) -> ExceptionDetail:
    item = require_exception(session, exception_ref)
    add_note(session, item, user, body.body, body.note_type)
    session.flush()
    return queries.get_exception(session, exception_ref, user)


@router.post("/{exception_ref}/actions", response_model=ExceptionActionResponse)
def act(
    exception_ref: str,
    body: ExceptionActionRequest,
    session: SessionDep,
    user: Annotated[User, Depends(require_role(Role.ANALYST))],
) -> ExceptionActionResponse:
    item = require_exception(session, exception_ref)
    approval = perform_action(session, item, user, body)
    session.flush()
    detail = queries.get_exception(session, exception_ref, user)
    return ExceptionActionResponse(**detail.model_dump(), approval_ref=approval)
