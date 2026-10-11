"""Baseline settlement reconciliation.

A settlement entry is matched when the batch has exactly one principal credit
for its payment and that credit equals the entry amount. Anything else is
unmatched. The comparison is deterministic and idempotent: the same entries
and credits always produce the same hash, so a replay does not invent a new
result.

Classifying *why* a row is unmatched (missing, duplicate, amount mismatch) is
intentionally not done here. That investigation is a separate piece of work.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal

from app.models.enums import ReconciliationStatus


@dataclass(frozen=True, slots=True)
class CreditFact:
    entry_ref: str
    payment_ref: str | None
    amount: Decimal


@dataclass(frozen=True, slots=True)
class EntryFact:
    entry_ref: str
    payment_ref: str | None
    amount: Decimal


@dataclass(frozen=True, slots=True)
class CompareResult:
    status: ReconciliationStatus
    matched_count: int
    unmatched_count: int
    unmatched_refs: list[str]
    matched_entry_refs: list[str]
    expected_total: Decimal
    recorded_total: Decimal
    variance: Decimal
    input_hash: str


def _money(value: Decimal) -> str:
    return format(value, "f")


def compare_batch(entries: list[EntryFact], credits: list[CreditFact]) -> CompareResult:
    """Match settlement entries to principal-credit ledger rows."""
    credits_by_payment: dict[str, list[CreditFact]] = {}
    for credit in credits:
        key = credit.payment_ref or ""
        credits_by_payment.setdefault(key, []).append(credit)

    matched_entries: list[str] = []
    unmatched: list[str] = []
    for entry in entries:
        group = credits_by_payment.get(entry.payment_ref or "", [])
        if len(group) == 1 and group[0].amount == entry.amount:
            matched_entries.append(entry.entry_ref)
        else:
            if group:
                unmatched.extend(credit.entry_ref for credit in group)
            else:
                unmatched.append(entry.entry_ref)

    expected = sum((entry.amount for entry in entries), Decimal("0"))
    recorded = sum((credit.amount for credit in credits), Decimal("0"))
    variance = recorded - expected
    status = (
        ReconciliationStatus.MATCHED
        if not unmatched and variance == 0
        else ReconciliationStatus.UNMATCHED
    )
    payload = {
        "entries": [
            {"ref": entry.entry_ref, "payment": entry.payment_ref, "amount": _money(entry.amount)}
            for entry in entries
        ],
        "credits": [
            {
                "ref": credit.entry_ref,
                "payment": credit.payment_ref,
                "amount": _money(credit.amount),
            }
            for credit in credits
        ],
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return CompareResult(
        status=status,
        matched_count=len(matched_entries),
        unmatched_count=len(unmatched),
        unmatched_refs=unmatched,
        matched_entry_refs=matched_entries,
        expected_total=expected,
        recorded_total=recorded,
        variance=variance,
        input_hash=digest,
    )
