"""Key/value metadata written by the seed (version, scenario clock, row counts)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core import clock
from app.db.base import Base


class SeedMetadata(Base):
    __tablename__ = "seed_metadata"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(255))
    updated_at: Mapped[datetime] = mapped_column(default=clock.now, onupdate=clock.now)
