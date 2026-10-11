"""Payment validation rules.

Each rule returns one outcome. A ``FAIL`` is what opens an exception; ``WARN`` is
recorded and does not hold the payment. The engine is pure: callers pass the
facts, including whether the end-to-end reference is already in use.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.models.enums import (
    AccountStatus,
    Currency,
    ExceptionSeverity,
    Rail,
    ValidationOutcome,
)

SWIFT_PURPOSE_THRESHOLD = Decimal("10000")
RAIL_CURRENCIES: dict[Rail, frozenset[Currency]] = {
    Rail.WIRE_USD: frozenset({Currency.USD}),
    Rail.ACH_USD: frozenset({Currency.USD}),
    Rail.SEPA_EUR: frozenset({Currency.EUR}),
    Rail.CHAPS_GBP: frozenset({Currency.GBP}),
    Rail.SWIFT_INTL: frozenset(Currency),
    Rail.INTERNAL_BOOK: frozenset(Currency),
}
BIC_RAILS = frozenset({Rail.WIRE_USD, Rail.SEPA_EUR, Rail.CHAPS_GBP, Rail.SWIFT_INTL})


def normalise_name(value: str) -> str:
    """Case- and whitespace-insensitive comparison key for beneficiary names."""
    return " ".join(value.upper().split())


@dataclass(frozen=True, slots=True)
class ValidationFacts:
    """Everything a rule is allowed to see. Money fields are ``Decimal``."""

    rail: Rail
    currency: Currency
    amount: Decimal
    usd_equivalent: Decimal
    instructed_name: str
    registered_name: str
    instructed_identifier: str
    registered_identifier: str
    instructed_bic: str | None
    account_status: AccountStatus
    account_currency: Currency
    available_balance: Decimal
    fee_amount: Decimal
    daily_limit_usd: Decimal
    purpose_code: str | None
    end_to_end_reference: str
    duplicate_reference: bool
    screening_hit: bool
    requested_value_date: date
    scenario_date: date
    quote_expires_at: datetime | None = None
    scenario_now: datetime | None = None


@dataclass(frozen=True, slots=True)
class RuleOutcome:
    rule_code: str
    rule_name: str
    outcome: ValidationOutcome
    severity: ExceptionSeverity
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)
    reason_code: str | None = None


def _fail(
    code: str,
    name: str,
    severity: ExceptionSeverity,
    message: str,
    reason_code: str,
    evidence: dict[str, Any],
) -> RuleOutcome:
    return RuleOutcome(code, name, ValidationOutcome.FAIL, severity, message, evidence, reason_code)


def _pass(
    code: str, name: str, message: str, evidence: dict[str, Any] | None = None
) -> RuleOutcome:
    return RuleOutcome(
        code,
        name,
        ValidationOutcome.PASS,
        ExceptionSeverity.LOW,
        message,
        evidence or {},
        None,
    )


def _warn(code: str, name: str, message: str, evidence: dict[str, Any]) -> RuleOutcome:
    return RuleOutcome(
        code, name, ValidationOutcome.WARN, ExceptionSeverity.LOW, message, evidence, None
    )


def evaluate(facts: ValidationFacts) -> list[RuleOutcome]:
    """Run every rule. Later failures are recorded; the primary one opens the exception."""
    return [
        _rule_name(facts),
        _rule_account_identifier(facts),
        _rule_bic(facts),
        _rule_duplicate(facts),
        _rule_limit(facts),
        _rule_currency_rail(facts),
        _rule_balance(facts),
        _rule_purpose(facts),
        _rule_value_date(facts),
        _rule_screening(facts),
        _rule_quote(facts),
        _rule_account_open(facts),
    ]


def primary_failure(outcomes: list[RuleOutcome]) -> RuleOutcome | None:
    """The hold reason: the highest-severity failure, screening first."""
    failures = [item for item in outcomes if item.outcome is ValidationOutcome.FAIL]
    if not failures:
        return None
    screening = [item for item in failures if item.reason_code == "SCREENING_REVIEW"]
    if screening:
        return screening[0]
    rank = {
        ExceptionSeverity.CRITICAL: 4,
        ExceptionSeverity.HIGH: 3,
        ExceptionSeverity.MEDIUM: 2,
        ExceptionSeverity.LOW: 1,
    }
    return max(failures, key=lambda item: rank[item.severity])


def _rule_name(facts: ValidationFacts) -> RuleOutcome:
    code, name = "VAL-001", "Beneficiary name matches the register"
    instructed = normalise_name(facts.instructed_name)
    registered = normalise_name(facts.registered_name)
    evidence = {"instructed_name": facts.instructed_name, "registered_name": facts.registered_name}
    if instructed != registered:
        return _fail(
            code,
            name,
            ExceptionSeverity.HIGH,
            "Instructed beneficiary name does not match the registered legal name.",
            "BENEFICIARY_NAME_MISMATCH",
            evidence,
        )
    return _pass(code, name, "Instructed name matches the registered beneficiary.", evidence)


def _rule_account_identifier(facts: ValidationFacts) -> RuleOutcome:
    code, name = "VAL-002", "Beneficiary account identifier matches the register"
    evidence = {
        "instructed_identifier": facts.instructed_identifier,
        "registered_identifier": facts.registered_identifier,
    }
    if facts.instructed_identifier.strip() != facts.registered_identifier.strip():
        return _fail(
            code,
            name,
            ExceptionSeverity.HIGH,
            "Instructed account identifier does not match the registered beneficiary.",
            "INVALID_ACCOUNT_IDENTIFIER",
            evidence,
        )
    return _pass(code, name, "Account identifier matches the register.", evidence)


def _rule_bic(facts: ValidationFacts) -> RuleOutcome:
    code, name = "VAL-003", "Beneficiary BIC present when the rail requires one"
    if facts.rail not in BIC_RAILS:
        return RuleOutcome(
            code,
            name,
            ValidationOutcome.SKIPPED,
            ExceptionSeverity.LOW,
            "This rail does not require a BIC.",
            {"rail": facts.rail.value},
        )
    if not (facts.instructed_bic or "").strip():
        return _fail(
            code,
            name,
            ExceptionSeverity.MEDIUM,
            "A BIC is required on this rail and none was supplied.",
            "MISSING_BENEFICIARY_BIC",
            {"rail": facts.rail.value},
        )
    return _pass(code, name, "BIC is present.", {"bic": facts.instructed_bic})


def _rule_duplicate(facts: ValidationFacts) -> RuleOutcome:
    code, name = "VAL-004", "End-to-end reference is unique for the customer"
    evidence = {"end_to_end_reference": facts.end_to_end_reference}
    if facts.duplicate_reference:
        return _fail(
            code,
            name,
            ExceptionSeverity.HIGH,
            "Another live payment already uses this end-to-end reference.",
            "DUPLICATE_REFERENCE",
            evidence,
        )
    return _pass(code, name, "End-to-end reference is unique.", evidence)


def _rule_limit(facts: ValidationFacts) -> RuleOutcome:
    code, name = "VAL-005", "Amount is within the customer daily limit"
    evidence = {
        "usd_equivalent": format(facts.usd_equivalent, "f"),
        "daily_limit_usd": format(facts.daily_limit_usd, "f"),
    }
    if facts.usd_equivalent > facts.daily_limit_usd:
        return _fail(
            code,
            name,
            ExceptionSeverity.HIGH,
            "USD equivalent exceeds the customer daily limit.",
            "AMOUNT_LIMIT_EXCEEDED",
            evidence,
        )
    return _pass(code, name, "Amount is within the daily limit.", evidence)


def _rule_currency_rail(facts: ValidationFacts) -> RuleOutcome:
    code, name = "VAL-006", "Currency is supported on the rail"
    allowed = RAIL_CURRENCIES[facts.rail]
    evidence = {"rail": facts.rail.value, "currency": facts.currency.value}
    if facts.currency not in allowed:
        return _fail(
            code,
            name,
            ExceptionSeverity.HIGH,
            f"{facts.currency.value} cannot be settled on {facts.rail.value}.",
            "UNSUPPORTED_CURRENCY_RAIL",
            evidence,
        )
    return _pass(code, name, "Currency is supported on the rail.", evidence)


def _rule_balance(facts: ValidationFacts) -> RuleOutcome:
    code, name = "VAL-007", "Available balance covers principal and fee"
    required = facts.amount + facts.fee_amount
    evidence = {
        "available_balance": format(facts.available_balance, "f"),
        "required": format(required, "f"),
        "currency": facts.account_currency.value,
    }
    if facts.account_currency is not facts.currency:
        return _warn(
            code,
            name,
            "Debit account currency differs from the payment currency; balance was not compared.",
            evidence,
        )
    if facts.available_balance < required:
        return _fail(
            code,
            name,
            ExceptionSeverity.MEDIUM,
            "Available balance does not cover the principal and the fee.",
            "INSUFFICIENT_FUNDS",
            evidence,
        )
    return _pass(code, name, "Available balance covers the payment.", evidence)


def _rule_purpose(facts: ValidationFacts) -> RuleOutcome:
    code, name = "VAL-008", "Purpose code present when required"
    needs_purpose = facts.rail is Rail.SWIFT_INTL and facts.amount >= SWIFT_PURPOSE_THRESHOLD
    if not needs_purpose:
        return RuleOutcome(
            code,
            name,
            ValidationOutcome.SKIPPED,
            ExceptionSeverity.LOW,
            "No purpose code is required for this payment.",
            {},
        )
    if not (facts.purpose_code or "").strip():
        return _fail(
            code,
            name,
            ExceptionSeverity.MEDIUM,
            "SWIFT payments at or above 10,000 require a purpose code.",
            "MISSING_PURPOSE_CODE",
            {"amount": format(facts.amount, "f")},
        )
    return _pass(code, name, "Purpose code is present.", {"purpose_code": facts.purpose_code})


def _rule_value_date(facts: ValidationFacts) -> RuleOutcome:
    code, name = "VAL-009", "Requested value date is not stale"
    evidence = {
        "requested_value_date": facts.requested_value_date.isoformat(),
        "scenario_date": facts.scenario_date.isoformat(),
    }
    if facts.requested_value_date < facts.scenario_date:
        return _fail(
            code,
            name,
            ExceptionSeverity.LOW,
            "Requested value date is before the scenario date.",
            "STALE_VALUE_DATE",
            evidence,
        )
    return _pass(code, name, "Requested value date is eligible.", evidence)


def _rule_screening(facts: ValidationFacts) -> RuleOutcome:
    code, name = "VAL-010", "Screening indicators clear"
    if facts.screening_hit:
        return _fail(
            code,
            name,
            ExceptionSeverity.CRITICAL,
            "A screening indicator is present. Financial Crime Risk must review.",
            "SCREENING_REVIEW",
            {"screening_hit": True},
        )
    return _pass(code, name, "No screening indicator.", {"screening_hit": False})


def _rule_quote(facts: ValidationFacts) -> RuleOutcome:
    code, name = "VAL-011", "Foreign-exchange quote still valid"
    if facts.quote_expires_at is None or facts.scenario_now is None:
        return RuleOutcome(
            code,
            name,
            ValidationOutcome.SKIPPED,
            ExceptionSeverity.LOW,
            "No foreign-exchange quote is attached.",
            {},
        )
    if facts.scenario_now >= facts.quote_expires_at:
        return _fail(
            code,
            name,
            ExceptionSeverity.MEDIUM,
            "The foreign-exchange quote expired before release.",
            "FX_QUOTE_EXPIRED",
            {"quote_expires_at": facts.quote_expires_at.isoformat()},
        )
    return _pass(code, name, "Foreign-exchange quote is still valid.", {})


def _rule_account_open(facts: ValidationFacts) -> RuleOutcome:
    code, name = "VAL-012", "Debit account is open"
    if facts.account_status is not AccountStatus.ACTIVE:
        return _fail(
            code,
            name,
            ExceptionSeverity.HIGH,
            f"Debit account is {facts.account_status.value}.",
            "INVALID_ACCOUNT_IDENTIFIER",
            {"account_status": facts.account_status.value},
        )
    return _pass(code, name, "Debit account is active.", {"account_status": "ACTIVE"})
