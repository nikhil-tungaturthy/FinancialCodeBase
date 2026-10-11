"""Demo identities."""

from __future__ import annotations

from app.models.enums import Role
from app.schemas.common import ApiModel


class UserOut(ApiModel):
    username: str
    display_name: str
    email: str
    role: Role
    team: str
    is_active: bool
