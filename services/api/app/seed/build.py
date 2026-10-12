"""Deterministic scenario seed.

Anchors (the hero payment, the incident batch, pending approvals) are written
with explicit values. Everything else is drawn from ``random.Random(20260318)``
so a second seed of an empty database reproduces the same rows.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from random import Random

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.actions import AuditAction
from app.audit.recorder import record_audit_event
from app.core.ids import (
    account_ref,
    approval_ref,
    batch_ref,
    beneficiary_ref,
    customer_ref,
    exception_ref,
    ledger_entry_ref,
    payment_correlation_id,
    payment_ref,
    settlement_entry_ref,
    stable_id,
    window_key,
)
from app.db.init import (
    SEED_PAYMENT_COUNT_KEY,
    SEED_SCENARIO_NOW_KEY,
    SEED_VERSION_KEY,
    get_seed_metadata,
    set_seed_metadata,
)
from app.domain.exceptions.classification import classify_exception
from app.domain.fees.service import LEGACY_DISPLAY_TARIFF, MODERN_TARIFF, compute_fee
from app.domain.money.fx import to_usd
from app.domain.payments.lifecycle import DEFAULT_EVENT_TYPE_FOR_STATUS
from app.domain.payments.references import channel_for_payment_ref
from app.domain.policies.reasons import reason_by_code
from app.domain.reconciliation.compare import (
    CreditFact,
    EntryFact,
    compare_batch,
    discrepancy_counts,
    serialize_discrepancies,
)
from app.domain.settlement.cutoff import classify_cutoff, get_rail_policy, window_for_business_date
from app.domain.validation.engine import ValidationFacts, evaluate, primary_failure
from app.models.approvals import ApprovalDecision, ApprovalRequest
from app.models.customers import BankAccount, Beneficiary, Customer
from app.models.enums import (
    AccountStatus,
    AccountType,
    ApprovalDecisionValue,
    ApprovalRiskLevel,
    ApprovalStatus,
    ApprovalSubjectType,
    BatchStatus,
    BeneficiaryVerificationStatus,
    BusinessRuleCategory,
    Currency,
    CustomerSegment,
    ExceptionAction,
    ExceptionSeverity,
    ExceptionStatus,
    FeeSource,
    IncidentSeverity,
    IncidentStatus,
    KycStatus,
    LedgerDirection,
    LedgerLeg,
    NoteType,
    PaymentEventType,
    PaymentPriority,
    PaymentStatus,
    PostingSource,
    Rail,
    RiskRating,
    RiskTier,
    Role,
    SettlementEntryStatus,
    ValidationOutcome,
)
from app.models.exceptions import ExceptionAssignment, ExceptionNote, PaymentException
from app.models.fees import FeeSchedule
from app.models.incidents import OperationalIncident
from app.models.ledger import LedgerEntry
from app.models.payments import Payment, PaymentEvent, PaymentInstruction, PaymentValidationResult
from app.models.reconciliation import ReconciliationResult
from app.models.rules import BusinessRule
from app.models.settlement import SettlementBatch, SettlementEntry
from app.models.users import User

SEED_VERSION = "2026.03.1"
RNG_SEED = 20260318
SCENARIO = datetime(2026, 3, 18, 18, 40, tzinfo=UTC)
HERO_NUMBER = 1042
HERO_EXCEPTION_NUMBER = 231
DISCREPANCY_BATCH = "SB-20260317-SEPA-02"
CLEAN_SEPA_BATCH = "SB-20260317-SEPA-01"
RESERVED_VALUE = date(2026, 3, 17)

DISCREPANCY_AMOUNTS: dict[int, Decimal] = {
    5101: Decimal("8420.00"),
    5102: Decimal("12650.00"),
    5103: Decimal("9800.00"),
    5104: Decimal("15340.00"),
    5105: Decimal("7200.00"),
    5106: Decimal("22100.00"),
    5107: Decimal("11450.00"),
    5108: Decimal("16780.00"),
    5109: Decimal("6350.00"),
    5110: Decimal("19870.00"),
    5111: Decimal("14200.00"),
    5112: Decimal("8750.00"),
    5113: Decimal("17640.00"),
    5114: Decimal("21117.00"),
    5140: Decimal("15450.00"),
    5143: Decimal("18450.00"),
    5147: Decimal("9800.00"),
}
DISCREPANCY_ENTRIES: dict[int, str] = {
    **{number: settlement_entry_ref(370 + index) for index, number in enumerate(range(5101, 5115))},
    5140: settlement_entry_ref(387),
    5143: settlement_entry_ref(388),
    5147: settlement_entry_ref(389),
}

USERS: tuple[tuple[str, str, Role, str], ...] = (
    ("priya.raman", "Priya Raman", Role.ANALYST, "Payments Operations"),
    ("marcus.okafor", "Marcus Okafor", Role.SUPERVISOR, "Payments Operations"),
    ("elena.vasquez", "Elena Vasquez", Role.PAYMENTS_MANAGER, "Payments Operations"),
    ("tomasz.nowak", "Tomasz Nowak", Role.RISK_OFFICER, "Financial Crime Risk"),
    ("aisha.bello", "Aisha Bello", Role.ANALYST, "Settlement & Reconciliation"),
    ("devon.hart", "Devon Hart", Role.ENGINEER, "Payments Platform Engineering"),
    ("system", "Meridian Flow System", Role.ENGINEER, "Platform"),
)

STATUS_BAG: tuple[PaymentStatus, ...] = (
    (PaymentStatus.RECONCILED,) * 50
    + (PaymentStatus.SETTLED,) * 18
    + (PaymentStatus.PENDING_SETTLEMENT,) * 10
    + (PaymentStatus.PROCESSING,) * 6
    + (PaymentStatus.APPROVED,) * 8
    + (PaymentStatus.FAILED,) * 5
    + (PaymentStatus.CANCELLED,) * 3
)

CHAIN: dict[PaymentStatus, tuple[PaymentStatus, ...]] = {
    PaymentStatus.RECONCILED: (
        PaymentStatus.CREATED,
        PaymentStatus.VALIDATING,
        PaymentStatus.APPROVED,
        PaymentStatus.PROCESSING,
        PaymentStatus.PENDING_SETTLEMENT,
        PaymentStatus.SETTLED,
        PaymentStatus.RECONCILED,
    ),
    PaymentStatus.SETTLED: (
        PaymentStatus.CREATED,
        PaymentStatus.VALIDATING,
        PaymentStatus.APPROVED,
        PaymentStatus.PROCESSING,
        PaymentStatus.PENDING_SETTLEMENT,
        PaymentStatus.SETTLED,
    ),
    PaymentStatus.PENDING_SETTLEMENT: (
        PaymentStatus.CREATED,
        PaymentStatus.VALIDATING,
        PaymentStatus.APPROVED,
        PaymentStatus.PROCESSING,
        PaymentStatus.PENDING_SETTLEMENT,
    ),
    PaymentStatus.PROCESSING: (
        PaymentStatus.CREATED,
        PaymentStatus.VALIDATING,
        PaymentStatus.APPROVED,
        PaymentStatus.PROCESSING,
    ),
    PaymentStatus.APPROVED: (
        PaymentStatus.CREATED,
        PaymentStatus.VALIDATING,
        PaymentStatus.APPROVED,
    ),
    PaymentStatus.HELD: (PaymentStatus.CREATED, PaymentStatus.VALIDATING, PaymentStatus.HELD),
    PaymentStatus.FAILED: (
        PaymentStatus.CREATED,
        PaymentStatus.VALIDATING,
        PaymentStatus.APPROVED,
        PaymentStatus.PROCESSING,
        PaymentStatus.FAILED,
    ),
    PaymentStatus.CANCELLED: (
        PaymentStatus.CREATED,
        PaymentStatus.VALIDATING,
        PaymentStatus.APPROVED,
        PaymentStatus.CANCELLED,
    ),
}


@dataclass
class Books:
    customers: list[Customer] = field(default_factory=list)
    by_currency: dict[Currency, list[tuple[Customer, BankAccount, Beneficiary]]] = field(
        default_factory=dict
    )
    users: dict[str, User] = field(default_factory=dict)
    payments: dict[int, Payment] = field(default_factory=dict)
    ledger_n: int = 10000
    journal_n: int = 1000
    entry_n: int = 1000
    recon_n: int = 1
    exception_n: int = 1
    approval_n: int = 1

    def ledger(self) -> str:
        self.ledger_n += 1
        return ledger_entry_ref(self.ledger_n)

    def journal(self) -> str:
        self.journal_n += 1
        return f"JRN-{self.journal_n:06d}"

    def entry(self) -> str:
        self.entry_n += 1
        return settlement_entry_ref(self.entry_n)


def run_seed(session: Session, *, force: bool = False) -> str:
    """Populate ``session``. Returns a short status string. Does not commit."""
    existing = get_seed_metadata(session, SEED_VERSION_KEY)
    if existing and not force:
        return f"already seeded ({existing})"
    if existing and force:
        raise RuntimeError("Refusing to reseed a populated database. Reset the file first.")
    rng = Random(RNG_SEED)
    books = Books()
    _users(session, books)
    _customers(session, books)
    _policies(session)
    session.flush()
    _population(session, books, rng)
    _hero(session, books)
    _discrepancy(session, books)
    _clean_sepa(session, books)
    session.flush()
    _batches(session, books)
    _approvals(session, books)
    _incident(session, books)
    count = session.scalar(select(func.count()).select_from(Payment)) or 0
    set_seed_metadata(session, SEED_VERSION_KEY, SEED_VERSION)
    set_seed_metadata(session, SEED_SCENARIO_NOW_KEY, SCENARIO.isoformat())
    set_seed_metadata(session, SEED_PAYMENT_COUNT_KEY, str(count))
    session.flush()
    return f"seeded {count} payments ({SEED_VERSION})"


def _users(session: Session, books: Books) -> None:
    for username, display, role, team in USERS:
        user = User(
            username=username,
            display_name=display,
            email=f"{username}@meridianglobal.example",
            role=role,
            team=team,
            is_active=True,
        )
        session.add(user)
        books.users[username] = user
    session.flush()


def _customers(session: Session, books: Books) -> None:
    specs = (
        (
            1,
            "Helios Capital Partners LLP",
            "Helios Capital",
            CustomerSegment.INSTITUTIONAL,
            "GB",
            RiskRating.HIGH,
            "Amelia Crowe",
            "5000000.00",
            (Currency.USD, Currency.EUR, Currency.GBP),
        ),
        (
            2,
            "Northbridge Municipal Treasury",
            "Northbridge",
            CustomerSegment.INSTITUTIONAL,
            "US",
            RiskRating.LOW,
            "Helen Cho",
            "8000000.00",
            (Currency.USD,),
        ),
        (
            3,
            "Larkspur Retail Cooperative",
            "Larkspur",
            CustomerSegment.RETAIL,
            "US",
            RiskRating.LOW,
            "Jonah Hale",
            "250000.00",
            (Currency.USD,),
        ),
        (
            4,
            "Cobalt and Pine Manufacturing",
            "Cobalt & Pine",
            CustomerSegment.CORPORATE,
            "US",
            RiskRating.MEDIUM,
            "Ruth Adler",
            "2000000.00",
            (Currency.USD, Currency.EUR),
        ),
        (
            5,
            "Veldt Logistics BV",
            "Veldt Logistics",
            CustomerSegment.CORPORATE,
            "NL",
            RiskRating.MEDIUM,
            "Pieter Vos",
            "3000000.00",
            (Currency.EUR,),
        ),
        (
            6,
            "Harbour and Grey Ltd",
            "Harbour & Grey",
            CustomerSegment.CORPORATE,
            "GB",
            RiskRating.MEDIUM,
            "Owen Clarke",
            "2500000.00",
            (Currency.GBP, Currency.EUR),
        ),
        (
            7,
            "Sable Peak Family Office",
            "Sable Peak",
            CustomerSegment.INSTITUTIONAL,
            "CH",
            RiskRating.HIGH,
            "Clara Meier",
            "6000000.00",
            (Currency.CHF, Currency.EUR),
        ),
        (
            8,
            "Kite Paper KK",
            "Kite Paper",
            CustomerSegment.CORPORATE,
            "JP",
            RiskRating.LOW,
            "Naomi Sato",
            "4000000.00",
            (Currency.JPY,),
        ),
        (
            9,
            "Orchid Clinics Group",
            "Orchid Clinics",
            CustomerSegment.CORPORATE,
            "SG",
            RiskRating.LOW,
            "Mei Tan",
            "1500000.00",
            (Currency.SGD, Currency.USD),
        ),
        (
            10,
            "Red Lantern Foods Inc",
            "Red Lantern",
            CustomerSegment.RETAIL,
            "US",
            RiskRating.LOW,
            "Jonah Hale",
            "150000.00",
            (Currency.USD,),
        ),
        (
            11,
            "Ostmark Components GmbH",
            "Ostmark",
            CustomerSegment.CORPORATE,
            "DE",
            RiskRating.MEDIUM,
            "Lukas Berger",
            "4000000.00",
            (Currency.EUR,),
        ),
        (
            12,
            "Meridian Treasury Desk",
            "Treasury Desk",
            CustomerSegment.INTERNAL,
            "US",
            RiskRating.LOW,
            "Devon Hart",
            "20000000.00",
            (Currency.USD, Currency.EUR, Currency.GBP),
        ),
    )
    beneficiary_names = {
        (1, Currency.USD): ("Aurelia Markets GmbH", "AURMDEFF", "Aurelia Markets Bank", "DE"),
        (1, Currency.EUR): ("Helios Euro Custody", "HELIUSDE", "Helios Custody", "DE"),
        (1, Currency.GBP): ("Helios Sterling Account", "HELIUSGB", "Helios London", "GB"),
    }
    account_n = 1
    beneficiary_n = 1
    for number, legal, short, segment, country, risk, manager, limit, currencies in specs:
        customer = Customer(
            customer_ref=customer_ref(int(number)),
            legal_name=str(legal),
            short_name=str(short),
            segment=segment,
            country=str(country),
            risk_rating=risk,
            kyc_status=KycStatus.VERIFIED,
            relationship_manager=str(manager),
            daily_limit_usd=Decimal(str(limit)),
            created_at=datetime(2024, 6, 1, tzinfo=UTC),
        )
        session.add(customer)
        books.customers.append(customer)
        session.flush()
        for currency in currencies:
            identifier = f"990{int(number):02d}{currency.value}{account_n:04d}"
            account = BankAccount(
                account_ref=account_ref(account_n),
                customer_id=customer.id,
                currency=currency,
                account_type=AccountType.OPERATING,
                identifier=identifier,
                masked_identifier=f"****{identifier[-4:]}",
                bic="MRDNGBA2",
                bank_name="Meridian Global Bank",
                available_balance=Decimal("50000000.00"),
                status=AccountStatus.ACTIVE,
            )
            session.add(account)
            preset = beneficiary_names.get((int(number), currency))
            if preset is None:
                name = f"{short} {currency.value} Beneficiary"
                bic, bank, ben_country = "BENFDEF1", "Fictional Beneficiary Bank", str(country)
            else:
                name, bic, bank, ben_country = preset
            beneficiary = Beneficiary(
                beneficiary_ref=beneficiary_ref(beneficiary_n),
                customer_id=customer.id,
                name=name,
                identifier=f"BEN{beneficiary_n:06d}{currency.value}",
                masked_identifier=f"****{beneficiary_n:04d}",
                bic=bic,
                bank_name=bank,
                country=ben_country,
                verification_status=BeneficiaryVerificationStatus.VERIFIED,
                registered_at=datetime(2025, 1, 15, tzinfo=UTC),
                last_used_at=SCENARIO - timedelta(days=2),
            )
            session.add(beneficiary)
            session.flush()
            books.by_currency.setdefault(currency, []).append((customer, account, beneficiary))
            account_n += 1
            beneficiary_n += 1


def _policies(session: Session) -> None:
    rules = [
        (
            "VAL-001",
            "Beneficiary name match",
            BusinessRuleCategory.VALIDATION,
            "Instructed name must match the registered beneficiary.",
            ExceptionSeverity.HIGH,
            "Payments Operations",
            "VB6 modExceptionRouting R03",
        ),
        (
            "VAL-002",
            "Account identifier match",
            BusinessRuleCategory.VALIDATION,
            "Instructed account identifier must match the register.",
            ExceptionSeverity.HIGH,
            "Payments Operations",
            "VB6 modExceptionRouting R01",
        ),
        (
            "VAL-004",
            "Duplicate reference",
            BusinessRuleCategory.VALIDATION,
            "End-to-end reference must be unique for the customer.",
            ExceptionSeverity.HIGH,
            "Payments Operations",
            "VB6 modExceptionRouting R04",
        ),
        (
            "VAL-005",
            "Daily limit",
            BusinessRuleCategory.LIMIT,
            "USD equivalent must sit within the customer daily limit.",
            ExceptionSeverity.HIGH,
            "Payments Operations",
            "VB6 modExceptionRouting R05",
        ),
        (
            "VAL-010",
            "Screening",
            BusinessRuleCategory.SCREENING,
            "Screening indicators must be clear before release.",
            ExceptionSeverity.CRITICAL,
            "Financial Crime Risk",
            "VB6 modExceptionRouting R07",
        ),
        (
            "FEE-001",
            "Legacy wire tariff",
            BusinessRuleCategory.FEE,
            "WIRE and SWIFT fees are priced by FEECALC01.",
            ExceptionSeverity.LOW,
            "Payments Platform Engineering",
            "COBOL FEECALC01",
        ),
        (
            "CUT-001",
            "Rail cutoff",
            BusinessRuleCategory.CUTOFF,
            "Value date follows the rail cutoff in the rail timezone.",
            ExceptionSeverity.MEDIUM,
            "Settlement & Reconciliation",
            None,
        ),
        (
            "APR-001",
            "Four-eyes release",
            BusinessRuleCategory.APPROVAL,
            "High-severity or high-value releases need a second person.",
            ExceptionSeverity.HIGH,
            "Payments Operations",
            "VB6 modExceptionRouting",
        ),
    ]
    for code, name, category, description, severity, owner, origin in rules:
        session.add(
            BusinessRule(
                rule_code=code,
                name=name,
                category=category,
                description=description,
                severity=severity,
                enabled=True,
                parameters={},
                owner_team=owner,
                legacy_origin=origin,
            )
        )
    effective = date(2026, 1, 1)
    for row in (*MODERN_TARIFF, *LEGACY_DISPLAY_TARIFF):
        session.add(
            FeeSchedule(
                rail=row.rail,
                currency=row.currency,
                segment=row.segment,
                fee_type=row.fee_type,
                flat_amount=row.flat_amount,
                bps=row.bps,
                min_fee=row.min_fee,
                max_fee=row.max_fee,
                effective_from=effective,
                effective_to=None,
                source=FeeSource.LEGACY_FEECALC01
                if row in LEGACY_DISPLAY_TARIFF
                else FeeSource.MODERN,
            )
        )


def _population(session: Session, books: Books, rng: Random) -> None:
    numbers = (
        list(range(1001, 1181))
        + list(range(2001, 2141))
        + list(range(5001, 5081))
        + list(range(8001, 8061))
    )
    numbers = [number for number in numbers if number != HERO_NUMBER]
    holds = set(rng.sample(numbers, 24))
    for number in numbers:
        status = PaymentStatus.HELD if number in holds else rng.choice(STATUS_BAG)
        currency = rng.choice(list(books.by_currency))
        customer, account, beneficiary = rng.choice(books.by_currency[currency])
        rail = _rail_for(currency, rng)
        created = _created_at(
            rng,
            in_flight=status
            in {
                PaymentStatus.HELD,
                PaymentStatus.APPROVED,
                PaymentStatus.PROCESSING,
                PaymentStatus.PENDING_SETTLEMENT,
            },
        )
        amount = _amount(rng, currency)
        instructed = beneficiary.name
        hold_kind = None
        if status is PaymentStatus.HELD:
            hold_kind = ("name", "bic", "screening")[number % 3]
            if hold_kind == "bic" and rail not in {
                Rail.WIRE_USD,
                Rail.SEPA_EUR,
                Rail.CHAPS_GBP,
                Rail.SWIFT_INTL,
            }:
                hold_kind = "name"
            if hold_kind == "name":
                instructed = f"{beneficiary.name} Ltd"
        _make_payment(
            session,
            books,
            number=number,
            customer=customer,
            account=account,
            beneficiary=beneficiary,
            rail=rail,
            amount=amount,
            created=created,
            status=status,
            instructed_name=instructed,
            priority=PaymentPriority.HIGH
            if status is PaymentStatus.HELD
            else PaymentPriority.NORMAL,
            remittance="Commercial settlement",
            hold_kind=hold_kind,
        )


def _hero(session: Session, books: Books) -> None:
    pool = books.by_currency[Currency.USD]
    customer, account, beneficiary = next(
        item
        for item in pool
        if item[0].legal_name.startswith("Helios") and item[2].name.startswith("Aurelia")
    )
    _make_payment(
        session,
        books,
        number=HERO_NUMBER,
        customer=customer,
        account=account,
        beneficiary=beneficiary,
        rail=Rail.WIRE_USD,
        amount=Decimal("480000.00"),
        created=datetime(2026, 3, 18, 17, 12, tzinfo=UTC),
        status=PaymentStatus.HELD,
        instructed_name="Aurelia Market GmbH",
        priority=PaymentPriority.URGENT,
        remittance="Quarterly margin call — Helios / Aurelia",
        exception_number=HERO_EXCEPTION_NUMBER,
        assignee="priya.raman",
        due_at=datetime(2026, 3, 18, 19, 20, tzinfo=UTC),
        risk_score=72,
    )
    payment = books.payments[HERO_NUMBER]
    beneficiary.verification_status = BeneficiaryVerificationStatus.NAME_MISMATCH_FLAGGED
    session.add(
        ExceptionNote(
            exception_id=payment.exceptions[0].id,
            author="priya.raman",
            note_type=NoteType.EVIDENCE,
            body=(
                "Registered beneficiary is Aurelia Markets GmbH. The instruction says "
                "Aurelia Market GmbH. Waiting on the relationship manager to confirm "
                "the legal name."
            ),
            created_at=datetime(2026, 3, 18, 17, 40, tzinfo=UTC),
        )
    )


def _discrepancy(session: Session, books: Books) -> None:
    pool = books.by_currency[Currency.EUR]
    customer, account, beneficiary = next(item for item in pool if item[0].short_name == "Ostmark")
    created = datetime(2026, 3, 17, 9, 5, tzinfo=UTC)
    for index, (number, amount) in enumerate(DISCREPANCY_AMOUNTS.items()):
        _make_payment(
            session,
            books,
            number=number,
            customer=customer,
            account=account,
            beneficiary=beneficiary,
            rail=Rail.SEPA_EUR,
            amount=amount,
            created=created + timedelta(minutes=4 * index),
            status=PaymentStatus.SETTLED,
            instructed_name=beneficiary.name,
            priority=PaymentPriority.NORMAL,
            remittance="SEPA file STL-20260317-02",
            value_date=RESERVED_VALUE,
            window_business_date=RESERVED_VALUE,
        )


def _clean_sepa(session: Session, books: Books) -> None:
    pool = books.by_currency[Currency.EUR]
    customer, account, beneficiary = next(
        item for item in pool if item[0].short_name == "Veldt Logistics"
    )
    created = datetime(2026, 3, 17, 7, 10, tzinfo=UTC)
    for index, number in enumerate(range(5201, 5209)):
        _make_payment(
            session,
            books,
            number=number,
            customer=customer,
            account=account,
            beneficiary=beneficiary,
            rail=Rail.SEPA_EUR,
            amount=Decimal(1200 + index * 340).quantize(Decimal("0.01")) + Decimal("0.50"),
            created=created + timedelta(minutes=3 * index),
            status=PaymentStatus.RECONCILED,
            instructed_name=beneficiary.name,
            priority=PaymentPriority.NORMAL,
            remittance="SEPA file STL-20260317-01",
            value_date=RESERVED_VALUE,
            window_business_date=RESERVED_VALUE,
        )


def _make_payment(
    session: Session,
    books: Books,
    *,
    number: int,
    customer: Customer,
    account: BankAccount,
    beneficiary: Beneficiary,
    rail: Rail,
    amount: Decimal,
    created: datetime,
    status: PaymentStatus,
    instructed_name: str,
    priority: PaymentPriority,
    remittance: str,
    exception_number: int | None = None,
    assignee: str | None = None,
    due_at: datetime | None = None,
    risk_score: int | None = None,
    value_date: date | None = None,
    window_business_date: date | None = None,
    hold_kind: str | None = None,
) -> Payment:
    ref = payment_ref(number)
    quote = compute_fee(rail, account.currency, customer.segment, amount)
    usd = to_usd(amount, account.currency)
    if window_business_date is not None:
        window = window_for_business_date(get_rail_policy(rail), window_business_date)
    else:
        window = classify_cutoff(rail.value, created)
        if rail is Rail.SEPA_EUR and window.value_date == RESERVED_VALUE:
            window = window_for_business_date(get_rail_policy(rail), date(2026, 3, 16))
    score = risk_score if risk_score is not None else (72 if usd >= Decimal("250000") else 28)
    if hold_kind == "screening":
        score = 95
    tier = RiskTier.HIGH if score >= 70 else RiskTier.MEDIUM if score >= 40 else RiskTier.LOW
    payment = Payment(
        payment_ref=ref,
        customer_id=customer.id,
        debit_account_id=account.id,
        beneficiary_id=beneficiary.id,
        channel=channel_for_payment_ref(ref),
        rail=rail,
        currency=account.currency,
        amount=amount,
        fee_amount=quote.amount,
        fee_currency=account.currency,
        usd_equivalent=usd,
        status=status,
        priority=priority,
        risk_score=score,
        risk_tier=tier,
        purpose_code="GDDS" if rail is Rail.SWIFT_INTL else "SUPP",
        end_to_end_reference=f"E2E-{number:04d}",
        remittance_info=remittance,
        requested_value_date=value_date or window.value_date,
        value_date=value_date or window.value_date,
        settlement_window_key=window.window_key
        if window_business_date is None
        else window_key(rail, window.business_date),
        settlement_cutoff_at=window.cutoff_at_utc,
        settlement_timezone=window.timezone,
        correlation_id=payment_correlation_id(ref),
        idempotency_key=stable_id("payment-idem", ref),
        failure_reason="Rail rejected the payment after submission"
        if status is PaymentStatus.FAILED
        else None,
        created_at=created,
        updated_at=created + timedelta(hours=2),
    )
    payment.customer = customer
    payment.debit_account = account
    payment.beneficiary = beneficiary
    session.add(payment)
    session.flush()
    _events(session, payment, status, created)
    instruction = PaymentInstruction(
        payment_id=payment.id,
        channel=payment.channel,
        instructed_beneficiary_name=instructed_name,
        instructed_identifier=beneficiary.identifier,
        instructed_bic=None if hold_kind == "bic" else beneficiary.bic,
        instructed_bank_name=beneficiary.bank_name,
        instructed_country=beneficiary.country,
        remittance_info=remittance,
        received_at=created,
        submitted_by=f"ops@{customer.short_name.split()[0].lower()}.example",
        raw_payload_hash=hashlib.sha256(f"{ref}|{instructed_name}|{amount}".encode()).hexdigest(),
    )
    session.add(instruction)
    payment.instruction = instruction
    reason = _validation(session, payment, instructed_name, created, hold_kind=hold_kind)
    if status is PaymentStatus.HELD:
        _exception(
            session,
            books,
            payment,
            created=created + timedelta(minutes=8),
            exception_number=exception_number,
            assignee=assignee,
            due_at=due_at,
            reason_code=reason or "BENEFICIARY_NAME_MISMATCH",
        )
    record_audit_event(
        session,
        actor="system",
        actor_role=Role.ENGINEER,
        action=AuditAction.PAYMENT_CREATED,
        entity_type="PAYMENT",
        entity_ref=ref,
        summary=f"Payment {ref} received on {payment.channel.value}",
        correlation_id=payment.correlation_id,
        occurred_at=created,
        stable_key=f"payment-created|{ref}",
        source_service="meridian-api",
    )
    books.payments[number] = payment
    return payment


def _events(session: Session, payment: Payment, status: PaymentStatus, created: datetime) -> None:
    previous: PaymentStatus | None = None
    for index, step in enumerate(CHAIN[status], start=1):
        event_type = DEFAULT_EVENT_TYPE_FOR_STATUS[step]
        if step is PaymentStatus.HELD:
            event_type = PaymentEventType.VALIDATION_FAILED
        session.add(
            PaymentEvent(
                payment_id=payment.id,
                sequence=index,
                event_type=event_type,
                from_status=previous,
                to_status=step,
                occurred_at=created + timedelta(minutes=2 * index),
                actor="system",
                summary=f"Status {step.value.lower().replace('_', ' ')}",
                detail={},
                correlation_id=payment.correlation_id,
            )
        )
        previous = step


def _validation(
    session: Session,
    payment: Payment,
    instructed_name: str,
    created: datetime,
    *,
    hold_kind: str | None = None,
) -> str | None:
    facts = ValidationFacts(
        rail=payment.rail,
        currency=payment.currency,
        amount=payment.amount,
        usd_equivalent=payment.usd_equivalent,
        instructed_name=instructed_name,
        registered_name=payment.beneficiary.name,
        instructed_identifier=payment.beneficiary.identifier,
        registered_identifier=payment.beneficiary.identifier,
        instructed_bic=None if hold_kind == "bic" else payment.beneficiary.bic,
        account_status=payment.debit_account.status,
        account_currency=payment.debit_account.currency,
        available_balance=payment.debit_account.available_balance,
        fee_amount=payment.fee_amount,
        daily_limit_usd=payment.customer.daily_limit_usd,
        purpose_code=payment.purpose_code,
        end_to_end_reference=payment.end_to_end_reference,
        duplicate_reference=False,
        screening_hit=hold_kind == "screening",
        requested_value_date=payment.requested_value_date,
        scenario_date=created.date(),
    )
    moment = created + timedelta(minutes=4)
    outcomes = evaluate(facts)
    for outcome in outcomes:
        session.add(
            PaymentValidationResult(
                payment_id=payment.id,
                rule_code=outcome.rule_code,
                rule_name=outcome.rule_name,
                outcome=outcome.outcome,
                severity=outcome.severity,
                message=outcome.message,
                evidence=dict(outcome.evidence),
                evaluated_at=moment,
            )
        )
    failure = primary_failure(outcomes)
    return failure.reason_code if failure is not None else None


def _exception(
    session: Session,
    books: Books,
    payment: Payment,
    *,
    created: datetime,
    exception_number: int | None,
    assignee: str | None,
    due_at: datetime | None,
    reason_code: str = "BENEFICIARY_NAME_MISMATCH",
) -> None:
    number = exception_number if exception_number is not None else books.exception_n
    if exception_number is None:
        books.exception_n += 1
        if books.exception_n == HERO_EXCEPTION_NUMBER:
            books.exception_n += 1
    routed = classify_exception(reason_code, payment.usd_equivalent, payment.customer.segment.value)
    policy = reason_by_code(reason_code)
    sla = policy.sla_minutes if policy is not None else 120
    item = PaymentException(
        exception_ref=exception_ref(number),
        payment_id=payment.id,
        reason_code=reason_code,
        reason_title=policy.title if policy is not None else reason_code,
        severity=routed.severity,
        status=ExceptionStatus.OPEN if assignee is None else ExceptionStatus.IN_REVIEW,
        opened_at=created,
        due_by=due_at or (created + timedelta(minutes=sla)),
        assigned_to_user_id=books.users[assignee].id if assignee else None,
        queue=routed.queue,
        summary=(policy.description[:240] if policy is not None else reason_code),
        resolved_at=None,
        resolution_code=None,
        correlation_id=payment.correlation_id,
        updated_at=created,
    )
    session.add(item)
    session.flush()
    if assignee:
        session.add(
            ExceptionAssignment(
                exception_id=item.id,
                assigned_to_user_id=books.users[assignee].id,
                assigned_by="system",
                assigned_at=created,
                note="Assigned by the intake sweep",
            )
        )
    record_audit_event(
        session,
        actor="system",
        actor_role=Role.ENGINEER,
        action=AuditAction.EXCEPTION_RAISED,
        entity_type="EXCEPTION",
        entity_ref=item.exception_ref,
        summary=item.summary,
        correlation_id=payment.correlation_id,
        occurred_at=created,
        stable_key=f"exception-raised|{item.exception_ref}",
    )
    payment.exceptions.append(item)


def _batches(session: Session, books: Books) -> None:
    groups: dict[tuple[Rail, date, bool], list[Payment]] = {}
    reserved = set(DISCREPANCY_AMOUNTS) | set(range(5201, 5209))
    for number, payment in books.payments.items():
        if number in reserved:
            continue
        if payment.status not in {PaymentStatus.SETTLED, PaymentStatus.RECONCILED}:
            continue
        reconciled = payment.status is PaymentStatus.RECONCILED
        groups.setdefault((payment.rail, payment.value_date, reconciled), []).append(payment)
    sequence_for: dict[tuple[Rail, date], int] = {}
    for (rail, value_date, reconciled), payments in sorted(
        groups.items(), key=lambda item: (item[0][1], item[0][0].value, item[0][2])
    ):
        sequence_for[(rail, value_date)] = sequence_for.get((rail, value_date), 0) + 1
        _close_batch(
            session,
            books,
            payments,
            reference=batch_ref(value_date, rail, sequence_for[(rail, value_date)]),
            reconciled=reconciled,
        )
    discrepancy = [books.payments[number] for number in DISCREPANCY_AMOUNTS]
    _close_batch(
        session,
        books,
        discrepancy,
        reference=DISCREPANCY_BATCH,
        reconciled=False,
        discrepancy=True,
    )
    clean = [books.payments[number] for number in range(5201, 5209)]
    _close_batch(session, books, clean, reference=CLEAN_SEPA_BATCH, reconciled=True)


def _close_batch(
    session: Session,
    books: Books,
    payments: list[Payment],
    *,
    reference: str,
    reconciled: bool,
    discrepancy: bool = False,
) -> None:
    if not payments:
        return
    sample = payments[0]
    expected = sum((payment.amount for payment in payments), Decimal("0"))
    posted_at = datetime.combine(sample.value_date, datetime.min.time(), tzinfo=UTC) + timedelta(
        hours=22
    )
    batch = SettlementBatch(
        batch_ref=reference,
        rail=sample.rail,
        currency=sample.currency,
        value_date=sample.value_date,
        window_key=sample.settlement_window_key or window_key(sample.rail, sample.value_date),
        timezone=sample.settlement_timezone or "UTC",
        cutoff_at=sample.settlement_cutoff_at or posted_at,
        status=BatchStatus.RECONCILED if reconciled else BatchStatus.SETTLED,
        expected_total=expected,
        recorded_total=expected,
        entry_count=len(payments),
        submitted_at=posted_at - timedelta(hours=1),
        settled_at=posted_at,
        reconciled_at=posted_at + timedelta(minutes=20) if reconciled else None,
        correlation_id=f"corr-batch-{reference}",
        created_at=posted_at - timedelta(hours=2),
        updated_at=posted_at,
    )
    session.add(batch)
    session.flush()
    credits: list[CreditFact] = []
    entries: list[EntryFact] = []
    for sequence, payment in enumerate(sorted(payments, key=lambda row: row.payment_ref), start=1):
        payment.settlement_batch_id = batch.id
        if discrepancy and payment.payment_ref == "MGB-PAY-5143":
            entry_reference = DISCREPANCY_ENTRIES[5143]
        elif discrepancy:
            number = int(payment.payment_ref.removeprefix("MGB-PAY-"))
            entry_reference = DISCREPANCY_ENTRIES[number]
        else:
            entry_reference = books.entry()
        session.add(
            SettlementEntry(
                entry_ref=entry_reference,
                batch_id=batch.id,
                payment_id=payment.id,
                amount=payment.amount,
                currency=payment.currency,
                status=SettlementEntryStatus.SETTLED,
                external_reference=f"EXT-{payment.payment_ref[-4:]}",
                settled_at=posted_at,
                sequence=sequence,
            )
        )
        entries.append(EntryFact(entry_reference, payment.payment_ref, payment.amount))
        if discrepancy and payment.payment_ref == "MGB-PAY-5143":
            _post_journal(
                session,
                payment,
                batch,
                "JRN-000612",
                posted_at,
                principal_credit="LE-002448",
                debit="LE-002447",
                fee_debit="LE-002449",
                fee_credit="LE-002450",
            )
            _post_journal(
                session,
                payment,
                batch,
                "JRN-000613",
                posted_at + timedelta(seconds=6),
                principal_credit="LE-002452",
                debit="LE-002451",
                fee_debit="LE-002453",
                fee_credit="LE-002454",
            )
            credits.append(CreditFact("LE-002448", payment.payment_ref, payment.amount))
            credits.append(CreditFact("LE-002452", payment.payment_ref, payment.amount))
        else:
            credit_ref = books.ledger()
            _post_journal(
                session, payment, batch, books.journal(), posted_at, principal_credit=credit_ref
            )
            credits.append(CreditFact(credit_ref, payment.payment_ref, payment.amount))
    compared = compare_batch(entries, credits)
    batch.recorded_total = compared.recorded_total
    if discrepancy:
        batch.status = BatchStatus.DISCREPANCY
        batch.correlation_id = "corr-settle-20260318-sepa02"
        _store_reconciliation(
            session, batch, compared, "RR-000061", posted_at + timedelta(minutes=27)
        )
    elif reconciled:
        batch.status = BatchStatus.RECONCILED
        books.recon_n += 1
        if books.recon_n == 61:
            books.recon_n += 1
        _store_reconciliation(
            session,
            batch,
            compared,
            f"RR-{books.recon_n:06d}",
            posted_at + timedelta(minutes=25),
        )
    session.flush()


def _post_journal(
    session: Session,
    payment: Payment,
    batch: SettlementBatch,
    journal: str,
    posted_at: datetime,
    *,
    principal_credit: str,
    debit: str | None = None,
    fee_debit: str | None = None,
    fee_credit: str | None = None,
) -> None:
    ccy = payment.currency.value
    legs = [
        (
            debit or f"LE-D{principal_credit[3:]}",
            LedgerDirection.DEBIT,
            payment.amount,
            LedgerLeg.PRINCIPAL,
            f"1100-CUST-{ccy}",
            "Customer principal",
        ),
        (
            principal_credit,
            LedgerDirection.CREDIT,
            payment.amount,
            LedgerLeg.PRINCIPAL,
            f"2010-NOSTRO-{ccy}",
            "Nostro principal",
        ),
        (
            fee_debit or f"LE-FD{principal_credit[3:]}",
            LedgerDirection.DEBIT,
            payment.fee_amount,
            LedgerLeg.FEE,
            f"1100-CUST-{ccy}",
            "Customer fee",
        ),
        (
            fee_credit or f"LE-FC{principal_credit[3:]}",
            LedgerDirection.CREDIT,
            payment.fee_amount,
            LedgerLeg.FEE,
            f"4100-FEE-INCOME-{ccy}",
            "Fee income",
        ),
    ]
    for entry_reference, direction, amount, leg, account, description in legs:
        if amount == 0:
            continue
        session.add(
            LedgerEntry(
                entry_ref=entry_reference,
                journal_ref=journal,
                payment_id=payment.id,
                batch_id=batch.id,
                account_code=account,
                direction=direction,
                amount=amount,
                currency=payment.currency,
                posted_at=posted_at,
                value_date=payment.value_date,
                description=f"{description} {payment.payment_ref}",
                posting_source=PostingSource.PAYMENT_ENGINE,
                leg=leg,
                correlation_id=batch.correlation_id,
            )
        )


def _store_reconciliation(
    session: Session,
    batch: SettlementBatch,
    compared: object,
    run_reference: str,
    run_at: datetime,
) -> None:
    session.add(
        ReconciliationResult(
            run_ref=run_reference,
            batch_id=batch.id,
            run_at=run_at,
            status=compared.status,  # type: ignore[attr-defined]
            matched_count=compared.matched_count,  # type: ignore[attr-defined]
            unmatched_count=compared.unmatched_count,  # type: ignore[attr-defined]
            expected_total=compared.expected_total,  # type: ignore[attr-defined]
            recorded_total=compared.recorded_total,  # type: ignore[attr-defined]
            variance=compared.variance,  # type: ignore[attr-defined]
            unmatched_refs=list(compared.unmatched_refs),  # type: ignore[attr-defined]
            discrepancies=serialize_discrepancies(compared.discrepancies),  # type: ignore[attr-defined]
            input_hash=compared.input_hash,  # type: ignore[attr-defined]
            notes="Baseline reconciliation of principal credits against settlement entries.",
        )
    )
    record_audit_event(
        session,
        actor="system",
        actor_role=Role.ENGINEER,
        action=AuditAction.RECONCILIATION_RUN,
        entity_type="SETTLEMENT_BATCH",
        entity_ref=batch.batch_ref,
        summary=f"Reconciliation {run_reference} recorded variance {compared.variance}",  # type: ignore[attr-defined]
        correlation_id=batch.correlation_id,
        occurred_at=run_at,
        metadata={
            "run_ref": run_reference,
            "input_hash": compared.input_hash,  # type: ignore[attr-defined]
            "discrepancy_counts": discrepancy_counts(compared.discrepancies),  # type: ignore[attr-defined]
        },
        stable_key=f"recon|{run_reference}",
        source_service="meridian-batch",
    )


def _approvals(session: Session, books: Books) -> None:
    holds = [
        payment
        for payment in books.payments.values()
        if payment.status is PaymentStatus.HELD and payment.payment_ref != "MGB-PAY-1042"
    ]
    holds.sort(key=lambda payment: payment.usd_equivalent, reverse=True)
    priya = books.users["priya.raman"]
    marcus = books.users["marcus.okafor"]
    for payment in holds[:3]:
        item = payment.exceptions[0]
        moment = item.opened_at + timedelta(minutes=15)
        reference = approval_ref(books.approval_n)
        books.approval_n += 1
        approval = ApprovalRequest(
            approval_ref=reference,
            subject_type=ApprovalSubjectType.PAYMENT_EXCEPTION,
            subject_ref=item.exception_ref,
            payment_ref=payment.payment_ref,
            requested_action=ExceptionAction.REPAIR_AND_RELEASE.value,
            summary=f"Repair and release {payment.payment_ref}",
            justification="Customer confirmed the registered legal name. Requesting release.",
            risk_level=ApprovalRiskLevel.HIGH
            if payment.usd_equivalent >= Decimal("100000")
            else ApprovalRiskLevel.MEDIUM,
            amount=payment.amount,
            currency=payment.currency,
            requested_by=priya.username,
            required_role=Role.SUPERVISOR,
            status=ApprovalStatus.PENDING,
            created_at=moment,
            expires_at=moment + timedelta(hours=8),
        )
        session.add(approval)
        item.status = ExceptionStatus.PENDING_APPROVAL
    if holds:
        item = holds[-1].exceptions[0]
        moment = datetime(2026, 3, 17, 16, 0, tzinfo=UTC)
        reference = approval_ref(books.approval_n)
        books.approval_n += 1
        session.add(
            ApprovalRequest(
                approval_ref=reference,
                subject_type=ApprovalSubjectType.PAYMENT_EXCEPTION,
                subject_ref=item.exception_ref,
                payment_ref=holds[-1].payment_ref,
                requested_action=ExceptionAction.RELEASE_AS_IS.value,
                summary=f"Release {holds[-1].payment_ref} without repair",
                justification="Analyst requested release before the name was confirmed.",
                risk_level=ApprovalRiskLevel.MEDIUM,
                amount=holds[-1].amount,
                currency=holds[-1].currency,
                requested_by=priya.username,
                required_role=Role.SUPERVISOR,
                status=ApprovalStatus.PENDING,
                created_at=moment,
                expires_at=moment + timedelta(hours=4),
            )
        )
    decided = ApprovalRequest(
        approval_ref=approval_ref(books.approval_n),
        subject_type=ApprovalSubjectType.PAYMENT_CANCELLATION,
        subject_ref="MGB-EXC-0000",
        payment_ref=None,
        requested_action=ExceptionAction.CANCEL_PAYMENT.value,
        summary="Cancel a duplicate retail ACH from 17 March",
        justification="Customer reported the file was submitted twice.",
        risk_level=ApprovalRiskLevel.LOW,
        amount=Decimal("860.00"),
        currency=Currency.USD,
        requested_by=priya.username,
        required_role=Role.SUPERVISOR,
        status=ApprovalStatus.APPROVED,
        created_at=datetime(2026, 3, 17, 11, 0, tzinfo=UTC),
        expires_at=datetime(2026, 3, 17, 19, 0, tzinfo=UTC),
        decided_at=datetime(2026, 3, 17, 11, 20, tzinfo=UTC),
    )
    session.add(decided)
    session.flush()
    session.add(
        ApprovalDecision(
            approval_request_id=decided.id,
            decided_by=marcus.username,
            decision=ApprovalDecisionValue.APPROVED,
            rationale="Duplicate confirmed against the earlier file.",
            decided_at=datetime(2026, 3, 17, 11, 20, tzinfo=UTC),
        )
    )


def _incident(session: Session, books: Books) -> None:
    session.add(
        OperationalIncident(
            incident_ref="INC-2026-0318-004",
            opened_at=datetime(2026, 3, 18, 1, 42, 17, tzinfo=UTC),
            severity=IncidentSeverity.SEV2,
            status=IncidentStatus.OPEN,
            service="meridian-batch/settlement",
            title="Settlement reconciliation variance on SB-20260317-SEPA-02",
            symptoms=[
                "RR-000061 recorded 253817.00 EUR against an expected 235367.00 EUR.",
                "MGB-PAY-5143 / SE-000388 has two nostro credits: LE-002448 and LE-002452.",
                "A database lock was followed by a retry that posted the same entry again.",
            ],
            affected_batch_ref=DISCREPANCY_BATCH,
            affected_payment_refs=["MGB-PAY-5143", "MGB-PAY-5140", "MGB-PAY-5147"],
            correlation_id="corr-settle-20260318-sepa02",
            evidence_path="shared/fixtures/incidents/INC-2026-0318-004",
            opened_by="system",
            resolved_at=None,
            resolution_summary=None,
        )
    )
    record_audit_event(
        session,
        actor="system",
        actor_role=Role.ENGINEER,
        action=AuditAction.INCIDENT_OPENED,
        entity_type="INCIDENT",
        entity_ref="INC-2026-0318-004",
        summary="Opened SEV2 settlement variance on SB-20260317-SEPA-02",
        correlation_id="corr-settle-20260318-sepa02",
        occurred_at=datetime(2026, 3, 18, 1, 42, 17, tzinfo=UTC),
        stable_key="incident-opened|INC-2026-0318-004",
        source_service="meridian-batch",
    )
    books.users["aisha.bello"]


def _rail_for(currency: Currency, rng: Random) -> Rail:
    if currency is Currency.USD:
        return rng.choice([Rail.WIRE_USD, Rail.ACH_USD, Rail.WIRE_USD])
    if currency is Currency.EUR:
        return Rail.SEPA_EUR
    if currency is Currency.GBP:
        return Rail.CHAPS_GBP
    return Rail.SWIFT_INTL


def _created_at(rng: Random, *, in_flight: bool) -> datetime:
    if in_flight:
        return SCENARIO - timedelta(hours=rng.randint(1, 6), minutes=rng.randint(0, 40))
    return SCENARIO - timedelta(
        days=rng.randint(1, 7), hours=rng.randint(1, 10), minutes=rng.randint(0, 50)
    )


def _amount(rng: Random, currency: Currency) -> Decimal:
    if currency is Currency.JPY:
        return Decimal(rng.randrange(80_000, 4_000_000, 1000))
    cents = rng.randrange(15_000, 18_000_000)
    return (Decimal(cents) / Decimal(100)).quantize(Decimal("0.01"))


def _unused(*_args: object) -> None:
    """Keep outcome import referenced for readers of the validation rows."""
    _ = ValidationOutcome.PASS
