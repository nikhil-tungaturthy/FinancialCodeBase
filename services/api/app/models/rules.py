"""Configurable business rules surfaced on the Policies page."""

from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONDict
from app.models.enums import BusinessRuleCategory, ExceptionSeverity


class BusinessRule(Base):
    __tablename__ = "business_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[BusinessRuleCategory] = mapped_column(index=True)
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[ExceptionSeverity]
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    parameters: Mapped[JSONDict] = mapped_column(default=dict)
    owner_team: Mapped[str] = mapped_column(String(128))
    legacy_origin: Mapped[str | None] = mapped_column(String(128))
