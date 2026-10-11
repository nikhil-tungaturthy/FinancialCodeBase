"""Application settings.

Settings are loaded with pydantic-settings using the ``MF_`` environment prefix and an
optional ``.env`` file at the repository root. Every component that needs configuration
goes through :func:`get_settings` so tests can replace values in one place.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# services/api/app/core/config.py -> core -> app -> api -> services -> <repo root>
REPO_ROOT: Path = Path(__file__).resolve().parents[4]

SERVICE_NAME = "meridian-api"
DEFAULT_DATABASE_URL = "sqlite:///./data/meridian_flow.db"
DEFAULT_SCENARIO_NOW = datetime(2026, 3, 18, 18, 40, 0, tzinfo=UTC)
DEFAULT_SEED = 20260318
DEFAULT_CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
API_PREFIX = "/api/v1"

LogFormat = Literal["json", "console"]

_SQLITE_FILE_PREFIX = "sqlite:///"


def resolve_sqlite_url(url: str, base_dir: Path) -> str:
    """Resolve a relative SQLite file URL against ``base_dir``.

    ``sqlite:///./data/x.db`` and ``sqlite:///data/x.db`` become absolute paths under
    ``base_dir``; in-memory URLs, absolute paths and non-SQLite URLs are returned unchanged.
    """
    if not url.startswith(_SQLITE_FILE_PREFIX):
        return url
    remainder = url[len(_SQLITE_FILE_PREFIX) :]
    if remainder in {"", ":memory:"} or remainder.startswith(("/", "file:")):
        return url
    path, separator, query = remainder.partition("?")
    resolved = (base_dir / path).resolve()
    return f"{_SQLITE_FILE_PREFIX}{resolved.as_posix()}{separator}{query}"


def sqlite_file_path(url: str) -> Path | None:
    """Return the on-disk path of a SQLite file URL, or ``None`` for other URLs."""
    if not url.startswith(_SQLITE_FILE_PREFIX):
        return None
    remainder = url[len(_SQLITE_FILE_PREFIX) :].partition("?")[0]
    if remainder in {"", ":memory:"} or remainder.startswith("file:"):
        return None
    return Path(remainder)


class Settings(BaseSettings):
    """Runtime configuration for the Meridian Flow API."""

    model_config = SettingsConfigDict(
        env_prefix="MF_",
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(
        default=DEFAULT_DATABASE_URL,
        description="SQLAlchemy URL. Relative SQLite paths resolve against the repository root.",
    )
    scenario_now: datetime = Field(
        default=DEFAULT_SCENARIO_NOW,
        description="The application's notion of 'now' (timezone-aware, normalised to UTC).",
    )
    seed: int = Field(default=DEFAULT_SEED, description="Deterministic seed for synthetic data.")
    log_level: str = "INFO"
    log_format: LogFormat = "json"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: list(DEFAULT_CORS_ORIGINS)
    )
    demo_default_user: str = "priya.raman"
    app_version: str = "0.1.0"
    environment: str = "demo"
    service_name: str = SERVICE_NAME
    api_prefix: str = API_PREFIX
    sql_echo: bool = False

    @field_validator("database_url", mode="after")
    @classmethod
    def _resolve_database_url(cls, value: str) -> str:
        return resolve_sqlite_url(value.strip(), REPO_ROOT)

    @field_validator("scenario_now", mode="after")
    @classmethod
    def _normalise_scenario_now(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("scenario_now must be timezone-aware (e.g. 2026-03-18T18:40:00Z)")
        return value.astimezone(UTC)

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalise_log_level(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("log_level must be a string")
        level = value.strip().upper()
        if logging.getLevelName(level) == f"Level {level}":
            raise ValueError(f"Unknown log level: {value!r}")
        return level

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            if text.startswith("["):
                parsed = json.loads(text)
                if not isinstance(parsed, list):
                    raise ValueError("cors_origins JSON must be a list of origins")
                return [str(item) for item in parsed]
            return [part.strip() for part in text.split(",") if part.strip()]
        return value

    @property
    def database_path(self) -> Path | None:
        """Absolute path of the SQLite database file, if the URL points at a file."""
        return sqlite_file_path(self.database_url)

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_sqlite_memory(self) -> bool:
        return self.is_sqlite and self.database_path is None

    @property
    def scenario_date_label(self) -> str:
        """Human label for the scenario date, e.g. ``Wed 18 Mar 2026``."""
        return self.scenario_now.strftime("%a %d %b %Y")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings instance (cached)."""
    return Settings()


def clear_settings_cache() -> None:
    """Forget the cached settings so the next :func:`get_settings` re-reads the environment."""
    get_settings.cache_clear()


SettingsDep = Annotated[Settings, Depends(get_settings)]
