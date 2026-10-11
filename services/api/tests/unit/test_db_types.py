"""Round trips through the aware-datetime and money type decorators on SQLite."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Dialect
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Session

from app.db.base import MoneyType, UTCDateTime
from app.models.enums import Currency, CustomerSegment, FeeSource, FeeType, Rail
from app.models.fees import FeeSchedule
from app.models.meta import SeedMetadata


def test_aware_datetime_round_trips_as_utc(session: Session) -> None:
    berlin = datetime(2026, 3, 18, 19, 40, 0, tzinfo=ZoneInfo("Europe/Berlin"))
    session.add(SeedMetadata(key="scenario_now", value="x", updated_at=berlin))
    session.commit()
    session.expunge_all()

    row = session.get(SeedMetadata, "scenario_now")
    assert row is not None
    assert row.updated_at.tzinfo is not None
    assert row.updated_at.utcoffset() == UTC.utcoffset(None)
    assert row.updated_at == berlin
    assert row.updated_at == datetime(2026, 3, 18, 18, 40, 0, tzinfo=UTC)

    stored = session.execute(
        select(SeedMetadata.__table__.c.updated_at).where(SeedMetadata.key == "scenario_now")
    ).scalar_one()
    assert stored == datetime(2026, 3, 18, 18, 40, 0, tzinfo=UTC)


def test_naive_datetime_is_rejected_on_write(session: Session) -> None:
    session.add(SeedMetadata(key="naive", value="x", updated_at=datetime(2026, 3, 18, 18, 40)))
    with pytest.raises(StatementError, match="naive"):
        session.commit()
    session.rollback()


def test_datetime_comparisons_work_in_sql(session: Session) -> None:
    early = datetime(2026, 3, 18, 1, 0, tzinfo=UTC)
    late = datetime(2026, 3, 18, 23, 0, tzinfo=UTC)
    session.add_all(
        [
            SeedMetadata(key="early", value="x", updated_at=early),
            SeedMetadata(key="late", value="x", updated_at=late),
        ]
    )
    session.commit()
    cutoff = datetime(2026, 3, 18, 20, 40, tzinfo=ZoneInfo("Europe/Berlin"))  # 19:40Z
    keys = session.scalars(select(SeedMetadata.key).where(SeedMetadata.updated_at > cutoff)).all()
    assert keys == ["late"]


def test_utc_datetime_result_parses_z_suffix_and_naive_as_utc() -> None:
    decorator = UTCDateTime()
    dialect: Dialect = _sqlite_dialect()
    assert decorator.process_result_value("2026-03-18T18:40:00Z", dialect) == datetime(
        2026, 3, 18, 18, 40, tzinfo=UTC
    )
    assert decorator.process_result_value("2026-03-18T18:40:00", dialect) == datetime(
        2026, 3, 18, 18, 40, tzinfo=UTC
    )
    assert decorator.process_result_value(None, dialect) is None


def test_money_round_trips_as_decimal(session: Session) -> None:
    session.add(
        FeeSchedule(
            rail=Rail.SEPA_EUR,
            currency=Currency.EUR,
            segment=CustomerSegment.CORPORATE,
            fee_type=FeeType.FLAT_PLUS_BPS,
            flat_amount=Decimal("0.35"),
            bps=1,
            min_fee=Decimal("0.35"),
            max_fee=Decimal("18450.00"),
            effective_from=date(2026, 1, 1),
            source=FeeSource.MODERN,
        )
    )
    session.commit()
    session.expunge_all()

    schedule = session.scalars(select(FeeSchedule)).one()
    assert isinstance(schedule.flat_amount, Decimal)
    assert schedule.flat_amount == Decimal("0.35")
    assert schedule.flat_amount.as_tuple().exponent == -4
    assert schedule.max_fee == Decimal("18450.00")


def test_money_rejects_floats_on_write(session: Session) -> None:
    session.add(
        FeeSchedule(
            rail=Rail.ACH_USD,
            currency=Currency.USD,
            segment=CustomerSegment.RETAIL,
            fee_type=FeeType.FLAT,
            flat_amount=0.35,  # type: ignore[arg-type]
            bps=0,
            min_fee=Decimal("0.35"),
            effective_from=date(2026, 1, 1),
        )
    )
    with pytest.raises(StatementError, match="float"):
        session.commit()
    session.rollback()


def test_money_type_scale_two_quantises_results() -> None:
    usd = MoneyType(18, 2)
    dialect = _sqlite_dialect()
    assert usd.process_result_value(480000.0, dialect) == Decimal("480000.00")
    assert usd.process_result_value(47.2, dialect) == Decimal("47.20")
    assert usd.process_result_value(18450, dialect) == Decimal("18450.00")
    assert usd.process_bind_param("12.345", dialect) == Decimal("12.35")
    assert usd.process_bind_param(None, dialect) is None
    with pytest.raises(TypeError):
        usd.process_bind_param(True, dialect)


def _sqlite_dialect() -> Dialect:
    from sqlalchemy.dialects import sqlite

    return sqlite.dialect()
