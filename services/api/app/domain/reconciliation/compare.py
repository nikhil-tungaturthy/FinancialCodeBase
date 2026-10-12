"""Settlement reconciliation.

A settlement entry is matched when the batch has exactly one principal credit
for its payment and that credit equals the entry amount. Anything else is
unmatched. The comparison is deterministic and idempotent: the same entries
and credits always produce the same hash, so a replay does not invent a new
result.

Each unmatched entry is also classified:

* ``MISSING`` — the settlement entry has no principal credit, or a principal
  credit has no settlement entry (``settlement_entry_ref`` is empty).
* ``DUPLICATE`` — the payment has more than one principal credit.
* ``AMOUNT_MISMATCH`` — exactly one principal credit exists and the amount
  differs from the settlement entry.

The classification does not change which refs are unmatched, and it is not
part of ``input_hash``. It does not post corrections, net reversing journals,
classify fee legs, or change payment status.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal

from app.models.enums import DiscrepancyKind, ReconciliationStatus


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
class Discrepancy:
    kind: DiscrepancyKind
    payment_ref: str | None
    settlement_entry_ref: str | None
    ledger_entry_refs: list[str]
    expected_amount: Decimal
    recorded_amount: Decimal


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
    discrepancies: list[Discrepancy]


def _money(value: Decimal) -> str:
    return format(value, "f")


def _payment_key(payment_ref: str | None) -> str:
    return payment_ref or ""


def serialize_discrepancies(items: list[Discrepancy]) -> list[dict[str, object]]:
    """JSON-ready discrepancy rows. Amounts are decimal strings."""
    return [
        {
            "kind": item.kind.value,
            "payment_ref": item.payment_ref,
            "settlement_entry_ref": item.settlement_entry_ref,
            "ledger_entry_refs": list(item.ledger_entry_refs),
            "expected_amount": _money(item.expected_amount),
            "recorded_amount": _money(item.recorded_amount),
        }
        for item in items
    ]


def discrepancy_counts(items: list[Discrepancy]) -> dict[str, int]:
    """Count of each kind, including zeroes, for the reconciliation audit event."""
    counts = {kind.value: 0 for kind in DiscrepancyKind}
    for item in items:
        counts[item.kind.value] += 1
    return counts


def compare_batch(entries: list[EntryFact], credits: list[CreditFact]) -> CompareResult:
    """Match settlement entries to principal-credit ledger rows and classify breaks."""
    credits_by_payment: dict[str, list[CreditFact]] = {}
    for credit in credits:
        credits_by_payment.setdefault(_payment_key(credit.payment_ref), []).append(credit)

    matched_entries: list[str] = []
    unmatched: list[str] = []
    discrepancies: list[Discrepancy] = []
    entry_keys: set[str] = set()
    for entry in entries:
        key = _payment_key(entry.payment_ref)
        entry_keys.add(key)
        group = credits_by_payment.get(key, [])
        if len(group) == 1 and group[0].amount == entry.amount:
            matched_entries.append(entry.entry_ref)
        else:
            if group:
                unmatched.extend(credit.entry_ref for credit in group)
                if len(group) == 1:
                    discrepancies.append(
                        Discrepancy(
                            kind=DiscrepancyKind.AMOUNT_MISMATCH,
                            payment_ref=entry.payment_ref,
                            settlement_entry_ref=entry.entry_ref,
                            ledger_entry_refs=[group[0].entry_ref],
                            expected_amount=entry.amount,
                            recorded_amount=group[0].amount,
                        )
                    )
                else:
                    discrepancies.append(
                        Discrepancy(
                            kind=DiscrepancyKind.DUPLICATE,
                            payment_ref=entry.payment_ref,
                            settlement_entry_ref=entry.entry_ref,
                            ledger_entry_refs=[credit.entry_ref for credit in group],
                            expected_amount=entry.amount,
                            recorded_amount=sum((credit.amount for credit in group), Decimal("0")),
                        )
                    )
            else:
                unmatched.append(entry.entry_ref)
                discrepancies.append(
                    Discrepancy(
                        kind=DiscrepancyKind.MISSING,
                        payment_ref=entry.payment_ref,
                        settlement_entry_ref=entry.entry_ref,
                        ledger_entry_refs=[],
                        expected_amount=entry.amount,
                        recorded_amount=Decimal("0"),
                    )
                )

    for key, group in credits_by_payment.items():
        if key in entry_keys or not group:
            continue
        discrepancies.append(
            Discrepancy(
                kind=DiscrepancyKind.MISSING,
                payment_ref=key or None,
                settlement_entry_ref=None,
                ledger_entry_refs=[credit.entry_ref for credit in group],
                expected_amount=Decimal("0"),
                recorded_amount=sum((credit.amount for credit in group), Decimal("0")),
            )
        )

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
        discrepancies=discrepancies,
    )
