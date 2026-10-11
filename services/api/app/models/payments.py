"""Payment aggregate: payment, original instruction, lifecycle events, validation results."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONDict, MoneyUSD, TimestampMixin
from app.models.enums import (
    Channel,
    Currency,
    ExceptionSeverity,
    PaymentEventType,
    PaymentPriority,
    PaymentStatus,
    Rail,
    RiskTier,
    ValidationOutcome,
)

if TYPE_CHECKING:
    from app.models.customers import BankAccount, Beneficiary, Customer
    from app.models.exceptions import PaymentException
    from app.models.ledger import LedgerEntry
    from app.models.settlement import SettlementBatch, SettlementEntry


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_status_created_at", "status", "created_at"),
        Index("ix_payments_rail_value_date", "rail", "value_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_ref: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    debit_account_id: Mapped[int] = mapped_column(ForeignKey("bank_accounts.id"), index=True)
    beneficiary_id: Mapped[int] = mapped_column(ForeignKey("beneficiaries.id"), index=True)
    channel: Mapped[Channel]
    rail: Mapped[Rail]
    currency: Mapped[Currency]
    amount: Mapped[Decimal]
    fee_amount: Mapped[Decimal]
    fee_currency: Mapped[Currency]
    usd_equivalent: Mapped[Decimal] = mapped_column(MoneyUSD)
    status: Mapped[PaymentStatus] = mapped_column(index=True)
    priority: Mapped[PaymentPriority] = mapped_column(default=PaymentPriority.NORMAL)
    risk_score: Mapped[int] = mapped_column(default=0)
    risk_tier: Mapped[RiskTier] = mapped_column(default=RiskTier.LOW)
    purpose_code: Mapped[str | None] = mapped_column(String(8))
    end_to_end_reference: Mapped[str] = mapped_column(String(64), index=True)
    remittance_info: Mapped[str | None] = mapped_column(String(280))
    requested_value_date: Mapped[date]
    value_date: Mapped[date]
    settlement_window_key: Mapped[str | None] = mapped_column(String(40), index=True)
    settlement_cutoff_at: Mapped[datetime | None]
    settlement_timezone: Mapped[str | None] = mapped_column(String(48))
    settlement_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("settlement_batches.id"), index=True
    )
    correlation_id: Mapped[str] = mapped_column(String(128), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True)
    failure_reason: Mapped[str | None] = mapped_column(String(280))

    customer: Mapped[Customer] = relationship(back_populates="payments")
    debit_account: Mapped[BankAccount] = relationship(back_populates="payments")
    beneficiary: Mapped[Beneficiary] = relationship(back_populates="payments")
    instruction: Mapped[PaymentInstruction | None] = relationship(
        back_populates="payment", uselist=False, cascade="all, delete-orphan"
    )
    events: Mapped[list[PaymentEvent]] = relationship(
        back_populates="payment",
        order_by="PaymentEvent.sequence",
        cascade="all, delete-orphan",
    )
    validation_results: Mapped[list[PaymentValidationResult]] = relationship(
        back_populates="payment",
        order_by="PaymentValidationResult.rule_code",
        cascade="all, delete-orphan",
    )
    exceptions: Mapped[list[PaymentException]] = relationship(
        back_populates="payment", order_by="PaymentException.opened_at"
    )
    settlement_batch: Mapped[SettlementBatch | None] = relationship(back_populates="payments")
    settlement_entries: Mapped[list[SettlementEntry]] = relationship(back_populates="payment")
    ledger_entries: Mapped[list[LedgerEntry]] = relationship(back_populates="payment")

    def __repr__(self) -> str:
        return f"Payment(ref={self.payment_ref!r}, status={self.status.value})"


class PaymentInstruction(Base):
    """The instruction exactly as received from the channel (one per payment)."""

    __tablename__ = "payment_instructions"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), unique=True)
    channel: Mapped[Channel]
    instructed_beneficiary_name: Mapped[str] = mapped_column(String(200))
    instructed_identifier: Mapped[str] = mapped_column(String(64))
    instructed_bic: Mapped[str | None] = mapped_column(String(32))
    instructed_bank_name: Mapped[str | None] = mapped_column(String(128))
    instructed_country: Mapped[str | None] = mapped_column(String(2))
    remittance_info: Mapped[str | None] = mapped_column(String(280))
    received_at: Mapped[datetime]
    submitted_by: Mapped[str] = mapped_column(String(254))
    raw_payload_hash: Mapped[str] = mapped_column(String(64))

    payment: Mapped[Payment] = relationship(back_populates="instruction")


class PaymentEvent(Base):
    __tablename__ = "payment_events"
    __table_args__ = (UniqueConstraint("payment_id", "sequence", name="payment_sequence"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), index=True)
    sequence: Mapped[int]
    event_type: Mapped[PaymentEventType]
    from_status: Mapped[PaymentStatus | None]
    to_status: Mapped[PaymentStatus | None]
    occurred_at: Mapped[datetime] = mapped_column(index=True)
    actor: Mapped[str] = mapped_column(String(64))
    summary: Mapped[str] = mapped_column(String(500))
    detail: Mapped[JSONDict] = mapped_column(default=dict)
    correlation_id: Mapped[str] = mapped_column(String(128), index=True)

    payment: Mapped[Payment] = relationship(back_populates="events")


class PaymentValidationResult(Base):
    __tablename__ = "payment_validation_results"
    __table_args__ = (
        Index("ix_payment_validation_results_payment_rule", "payment_id", "rule_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), index=True)
    rule_code: Mapped[str] = mapped_column(String(16))
    rule_name: Mapped[str] = mapped_column(String(128))
    outcome: Mapped[ValidationOutcome]
    severity: Mapped[ExceptionSeverity]
    message: Mapped[str] = mapped_column(Text)
    evidence: Mapped[JSONDict] = mapped_column(default=dict)
    evaluated_at: Mapped[datetime]

    payment: Mapped[Payment] = relationship(back_populates="validation_results")
