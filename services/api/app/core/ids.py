"""Deterministic identifiers and public reference formatters.

Seeded data must be reproducible, so anything that needs a UUID derives it with
:func:`stable_uuid` from a stable key. Public references (``MGB-PAY-1042``,
``SB-20260317-SEPA-02`` ...) are formatted here so every service agrees on their shape.
"""

from __future__ import annotations

import re
import uuid
from datetime import date
from enum import Enum
from typing import Final

NAMESPACE_MERIDIAN: Final[uuid.UUID] = uuid.uuid5(uuid.NAMESPACE_URL, "urn:meridian-flow")

PAYMENT_REF_PREFIX: Final = "MGB-PAY-"
EXCEPTION_REF_PREFIX: Final = "MGB-EXC-"
APPROVAL_REF_PREFIX: Final = "MGB-APR-"

RAIL_SHORT_CODES: Final[dict[str, str]] = {
    "WIRE_USD": "WIRE",
    "ACH_USD": "ACH",
    "SEPA_EUR": "SEPA",
    "CHAPS_GBP": "CHAPS",
    "SWIFT_INTL": "SWIFT",
    "INTERNAL_BOOK": "BOOK",
}

_PAYMENT_REF_RE = re.compile(r"^MGB-PAY-(\d{4,})$")
_BATCH_REF_RE = re.compile(r"^SB-(\d{8})-([A-Z]+)-(\d{2,})$")


def _code(value: str | Enum) -> str:
    return value.value if isinstance(value, Enum) else value


def stable_uuid(*parts: object) -> uuid.UUID:
    """A uuid5 derived from ``parts`` (joined with ``|``); identical inputs give identical ids."""
    key = "|".join(str(part) for part in parts)
    return uuid.uuid5(NAMESPACE_MERIDIAN, key)


def stable_id(*parts: object) -> str:
    return str(stable_uuid(*parts))


def new_correlation_id(prefix: str = "corr-req") -> str:
    """A fresh correlation id for an inbound request that did not supply one."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def payment_ref(number: int) -> str:
    return f"{PAYMENT_REF_PREFIX}{number}"


def parse_payment_ref(ref: str) -> int:
    match = _PAYMENT_REF_RE.match(ref.strip().upper())
    if match is None:
        raise ValueError(f"Not a payment reference: {ref!r}")
    return int(match.group(1))


def exception_ref(number: int) -> str:
    return f"{EXCEPTION_REF_PREFIX}{number:04d}"


def approval_ref(number: int) -> str:
    return f"{APPROVAL_REF_PREFIX}{number:04d}"


def customer_ref(number: int) -> str:
    return f"CUST-{number:04d}"


def account_ref(number: int) -> str:
    return f"ACC-{number:04d}"


def beneficiary_ref(number: int) -> str:
    return f"BEN-{number:04d}"


def rail_short_code(rail: str | Enum) -> str:
    code = _code(rail)
    try:
        return RAIL_SHORT_CODES[code]
    except KeyError as exc:
        raise ValueError(f"Unknown rail: {code!r}") from exc


def batch_ref(value_date: date, rail: str | Enum, sequence: int) -> str:
    """``SB-20260317-SEPA-02`` style settlement batch reference."""
    return f"SB-{value_date:%Y%m%d}-{rail_short_code(rail)}-{sequence:02d}"


def parse_batch_ref(ref: str) -> tuple[date, str, int]:
    """Split a batch reference into (value_date, rail short code, sequence)."""
    match = _BATCH_REF_RE.match(ref.strip().upper())
    if match is None:
        raise ValueError(f"Not a settlement batch reference: {ref!r}")
    raw_date, short_code, sequence = match.groups()
    parsed = date(int(raw_date[:4]), int(raw_date[4:6]), int(raw_date[6:8]))
    return parsed, short_code, int(sequence)


def settlement_entry_ref(number: int) -> str:
    return f"SE-{number:06d}"


def ledger_entry_ref(number: int) -> str:
    return f"LE-{number:06d}"


def journal_ref(number: int) -> str:
    return f"JRN-{number:06d}"


def reconciliation_run_ref(number: int) -> str:
    return f"RR-{number:06d}"


def incident_ref(opened_on: date, sequence: int) -> str:
    """``INC-2026-0318-004`` style incident reference."""
    return f"INC-{opened_on:%Y}-{opened_on:%m%d}-{sequence:03d}"


def validation_rule_code(number: int) -> str:
    return f"VAL-{number:03d}"


def payment_correlation_id(ref: str) -> str:
    """``corr-pay-1042`` for ``MGB-PAY-1042``."""
    return f"corr-pay-{parse_payment_ref(ref)}"


def window_key(rail: str | Enum, business_date: date) -> str:
    """Settlement window key, e.g. ``WIRE_USD:2026-03-18``."""
    return f"{_code(rail)}:{business_date.isoformat()}"
