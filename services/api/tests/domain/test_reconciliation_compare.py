"""Discrepancy classification for settlement reconciliation."""

from __future__ import annotations

from decimal import Decimal

from app.domain.reconciliation.compare import CreditFact, EntryFact, compare_batch
from app.models.enums import DiscrepancyKind, ReconciliationStatus


def test_matched_entry_has_no_discrepancy() -> None:
    result = compare_batch(
        [EntryFact("SE-1", "MGB-PAY-1", Decimal("10.00"))],
        [CreditFact("LE-1", "MGB-PAY-1", Decimal("10.00"))],
    )
    assert result.status is ReconciliationStatus.MATCHED
    assert result.unmatched_refs == []
    assert result.discrepancies == []
    assert result.variance == Decimal("0.00")


def test_missing_principal_credit_keeps_the_settlement_ref() -> None:
    result = compare_batch(
        [EntryFact("SE-1", "MGB-PAY-1", Decimal("10.00"))],
        [],
    )
    assert result.unmatched_refs == ["SE-1"]
    assert len(result.discrepancies) == 1
    item = result.discrepancies[0]
    assert item.kind is DiscrepancyKind.MISSING
    assert item.payment_ref == "MGB-PAY-1"
    assert item.settlement_entry_ref == "SE-1"
    assert item.ledger_entry_refs == []
    assert item.expected_amount == Decimal("10.00")
    assert item.recorded_amount == Decimal("0")


def test_amount_mismatch_links_the_single_credit() -> None:
    result = compare_batch(
        [EntryFact("SE-1", "MGB-PAY-1", Decimal("10.00"))],
        [CreditFact("LE-1", "MGB-PAY-1", Decimal("12.50"))],
    )
    assert result.unmatched_refs == ["LE-1"]
    item = result.discrepancies[0]
    assert item.kind is DiscrepancyKind.AMOUNT_MISMATCH
    assert item.settlement_entry_ref == "SE-1"
    assert item.ledger_entry_refs == ["LE-1"]
    assert item.expected_amount == Decimal("10.00")
    assert item.recorded_amount == Decimal("12.50")


def test_duplicate_credits_match_the_sepa_worked_example() -> None:
    amount = Decimal("18450.00")
    result = compare_batch(
        [EntryFact("SE-000388", "MGB-PAY-5143", amount)],
        [
            CreditFact("LE-002448", "MGB-PAY-5143", amount),
            CreditFact("LE-002452", "MGB-PAY-5143", amount),
        ],
    )
    assert result.unmatched_refs == ["LE-002448", "LE-002452"]
    assert result.matched_count == 0
    assert result.variance == amount
    item = result.discrepancies[0]
    assert item.kind is DiscrepancyKind.DUPLICATE
    assert item.payment_ref == "MGB-PAY-5143"
    assert item.settlement_entry_ref == "SE-000388"
    assert item.ledger_entry_refs == ["LE-002448", "LE-002452"]
    assert item.expected_amount == amount
    assert item.recorded_amount == Decimal("36900.00")


def test_orphan_credit_is_missing_and_stays_out_of_unmatched_refs() -> None:
    result = compare_batch(
        [EntryFact("SE-1", "MGB-PAY-1", Decimal("10.00"))],
        [
            CreditFact("LE-1", "MGB-PAY-1", Decimal("10.00")),
            CreditFact("LE-9", "MGB-PAY-9", Decimal("4.00")),
        ],
    )
    assert result.unmatched_refs == []
    assert result.status is ReconciliationStatus.UNMATCHED
    assert len(result.discrepancies) == 1
    orphan = result.discrepancies[0]
    assert orphan.kind is DiscrepancyKind.MISSING
    assert orphan.settlement_entry_ref is None
    assert orphan.payment_ref == "MGB-PAY-9"
    assert orphan.ledger_entry_refs == ["LE-9"]
    assert orphan.expected_amount == Decimal("0")
    assert orphan.recorded_amount == Decimal("4.00")


def test_input_hash_is_stable_and_ignores_classification() -> None:
    entries = [EntryFact("SE-000388", "MGB-PAY-5143", Decimal("18450.00"))]
    credits = [
        CreditFact("LE-002448", "MGB-PAY-5143", Decimal("18450.00")),
        CreditFact("LE-002452", "MGB-PAY-5143", Decimal("18450.00")),
    ]
    first = compare_batch(entries, credits)
    second = compare_batch(entries, credits)
    assert first.input_hash == second.input_hash
    assert first.discrepancies[0].kind is DiscrepancyKind.DUPLICATE
    assert "DUPLICATE" not in first.input_hash
