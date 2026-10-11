"""Settings resolution, scenario clock helpers, id formatters and references."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from app.core import clock
from app.core.config import REPO_ROOT, Settings, resolve_sqlite_url, sqlite_file_path
from app.core.ids import (
    approval_ref,
    batch_ref,
    exception_ref,
    incident_ref,
    journal_ref,
    ledger_entry_ref,
    parse_batch_ref,
    parse_payment_ref,
    payment_correlation_id,
    payment_ref,
    reconciliation_run_ref,
    settlement_entry_ref,
    stable_uuid,
    window_key,
)
from app.domain.payments.references import (
    CHANNEL_REFERENCE_BLOCKS,
    block_range,
    channel_for_payment_ref,
    ordinal_for_payment_ref,
    payment_ref_for,
)
from app.models.enums import Channel, Rail


def test_repo_root_points_at_the_workspace() -> None:
    assert (REPO_ROOT / "pyproject.toml").is_file()
    assert (REPO_ROOT / "services" / "api").is_dir()


def test_default_database_url_resolves_under_repo_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MF_DATABASE_URL", raising=False)
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert (
        settings.database_url == f"sqlite:///{(REPO_ROOT / 'data' / 'meridian_flow.db').as_posix()}"
    )
    assert settings.database_path == REPO_ROOT / "data" / "meridian_flow.db"
    assert settings.is_sqlite and not settings.is_sqlite_memory


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("sqlite://", "sqlite://"),
        ("sqlite:///:memory:", "sqlite:///:memory:"),
        ("sqlite:////abs/path.db", "sqlite:////abs/path.db"),
        ("postgresql://u:p@h/db", "postgresql://u:p@h/db"),
    ],
)
def test_non_relative_urls_are_untouched(url: str, expected: str) -> None:
    assert resolve_sqlite_url(url, Path("/base")) == expected


def test_relative_sqlite_url_resolution_keeps_query() -> None:
    assert resolve_sqlite_url("sqlite:///data/x.db?mode=rw", Path("/base")) == (
        "sqlite:////base/data/x.db?mode=rw"
    )
    assert sqlite_file_path("sqlite:////base/data/x.db?mode=rw") == Path("/base/data/x.db")
    assert sqlite_file_path("sqlite://") is None


def test_settings_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MF_SCENARIO_NOW", "2026-03-18T13:40:00-05:00")
    monkeypatch.setenv("MF_CORS_ORIGINS", "http://a.example, http://b.example")
    monkeypatch.setenv("MF_LOG_LEVEL", "debug")
    monkeypatch.setenv("MF_DATABASE_URL", "sqlite://")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.scenario_now == datetime(2026, 3, 18, 18, 40, tzinfo=UTC)
    assert settings.scenario_now.tzinfo is UTC
    assert settings.cors_origins == ["http://a.example", "http://b.example"]
    assert settings.log_level == "DEBUG"
    assert settings.is_sqlite_memory
    assert settings.scenario_date_label == "Wed 18 Mar 2026"


def test_settings_reject_naive_scenario_now_and_bad_log_level() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        Settings(_env_file=None, scenario_now="2026-03-18T18:40:00")  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="Unknown log level"):
        Settings(_env_file=None, log_level="LOUD")  # type: ignore[call-arg]


def test_scenario_clock_defaults() -> None:
    assert clock.now() == datetime(2026, 3, 18, 18, 40, tzinfo=UTC)
    assert clock.today() == date(2026, 3, 18)
    assert clock.business_day_label() == "Wed 18 Mar 2026"
    assert clock.utc_time_label() == "18:40 UTC"


def test_clock_frozen_override_is_scoped() -> None:
    pinned = datetime(2026, 3, 19, 9, 0, tzinfo=ZoneInfo("Europe/London"))
    with clock.frozen(pinned) as moment:
        assert moment.tzinfo is UTC
        assert clock.now() == pinned
        assert clock.today() == date(2026, 3, 19)
    assert clock.now() == datetime(2026, 3, 18, 18, 40, tzinfo=UTC)


def test_to_local_and_minutes_until() -> None:
    cutoff = datetime(2026, 3, 18, 20, 30, tzinfo=UTC)
    local = clock.to_local(cutoff, "America/New_York")
    assert local.hour == 16 and local.minute == 30
    assert local.utcoffset() == timedelta(hours=-4)
    assert clock.minutes_until(cutoff) == 110
    assert clock.minutes_until(cutoff - timedelta(hours=3)) == -70
    assert clock.minutes_until(cutoff, reference=cutoff - timedelta(seconds=30)) == 0
    assert clock.minutes_until(cutoff, reference=cutoff + timedelta(seconds=30)) == -1
    assert clock.age_minutes(datetime(2026, 3, 18, 17, 52, 12, tzinfo=UTC)) == 47
    assert clock.age_minutes(cutoff) == 0


def test_ensure_aware_and_to_utc() -> None:
    naive = datetime(2026, 3, 18, 18, 40)
    assert clock.ensure_aware(naive).tzinfo is UTC
    paris = datetime(2026, 3, 18, 19, 40, tzinfo=ZoneInfo("Europe/Paris"))
    assert clock.to_utc(paris) == datetime(2026, 3, 18, 18, 40, tzinfo=UTC)


def test_reference_formatters() -> None:
    assert payment_ref(1042) == "MGB-PAY-1042"
    assert parse_payment_ref("mgb-pay-1042") == 1042
    assert exception_ref(231) == "MGB-EXC-0231"
    assert approval_ref(307) == "MGB-APR-0307"
    assert batch_ref(date(2026, 3, 17), Rail.SEPA_EUR, 2) == "SB-20260317-SEPA-02"
    assert batch_ref(date(2026, 3, 5), "CHAPS_GBP", 1) == "SB-20260305-CHAPS-01"
    assert parse_batch_ref("SB-20260317-SEPA-02") == (date(2026, 3, 17), "SEPA", 2)
    assert settlement_entry_ref(388) == "SE-000388"
    assert ledger_entry_ref(123) == "LE-000123"
    assert journal_ref(45) == "JRN-000045"
    assert reconciliation_run_ref(12) == "RR-000012"
    assert incident_ref(date(2026, 3, 18), 4) == "INC-2026-0318-004"
    assert payment_correlation_id("MGB-PAY-1042") == "corr-pay-1042"
    assert window_key(Rail.WIRE_USD, date(2026, 3, 18)) == "WIRE_USD:2026-03-18"
    with pytest.raises(ValueError):
        parse_payment_ref("PAY-1")
    with pytest.raises(ValueError):
        batch_ref(date(2026, 3, 17), "TELEX", 1)


def test_stable_uuid_is_deterministic_and_input_sensitive() -> None:
    assert stable_uuid("audit", "MGB-PAY-1042", 1) == stable_uuid("audit", "MGB-PAY-1042", 1)
    assert stable_uuid("audit", "MGB-PAY-1042", 1) != stable_uuid("audit", "MGB-PAY-1042", 2)
    assert stable_uuid("a").version == 5


def test_channel_reference_blocks() -> None:
    assert CHANNEL_REFERENCE_BLOCKS == {
        Channel.PORTAL: 1000,
        Channel.API: 2000,
        Channel.FILE: 5000,
        Channel.BRANCH: 8000,
    }
    assert payment_ref_for(Channel.PORTAL, 43) == "MGB-PAY-1042"
    assert payment_ref_for(Channel.API, 1) == "MGB-PAY-2000"
    assert payment_ref_for(Channel.FILE, 144) == "MGB-PAY-5143"
    assert payment_ref_for(Channel.BRANCH, 1) == "MGB-PAY-8000"
    assert block_range(Channel.API) == (2000, 4999)
    assert block_range(Channel.BRANCH) == (8000, 9999)
    assert channel_for_payment_ref("MGB-PAY-1042") is Channel.PORTAL
    assert channel_for_payment_ref("MGB-PAY-5143") is Channel.FILE
    assert channel_for_payment_ref("MGB-PAY-8003") is Channel.BRANCH
    assert ordinal_for_payment_ref("MGB-PAY-1042") == 43
    with pytest.raises(ValueError):
        payment_ref_for(Channel.PORTAL, 0)
    with pytest.raises(ValueError):
        payment_ref_for(Channel.PORTAL, 1001)
