"""Health, readiness and scenario metadata."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from app.schemas.common import ApiModel


class HealthResponse(ApiModel):
    status: Literal["ok"] = "ok"
    service: str
    version: str
    scenario_now: datetime


class ReadyResponse(ApiModel):
    status: Literal["ready", "not_ready"]
    database: Literal["ok", "error"]
    seeded: bool
    seed_version: str | None = None
    detail: str | None = None


class ScenarioMeta(ApiModel):
    scenario_now: datetime
    scenario_date: date
    business_day_label: str
    seed_version: str | None = None
    display_timezone: str = "UTC"
    fx_reference_rates: dict[str, str]
    fx_rates_label: str
    environment: str
