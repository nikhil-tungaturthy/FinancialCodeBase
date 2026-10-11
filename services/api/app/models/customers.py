"""Customers, their bank accounts and registered beneficiaries."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core import clock
from app.db.base import Base, MoneyUSD
from app.models.enums import (
    AccountStatus,
    AccountType,
    BeneficiaryVerificationStatus,
    Currency,
    CustomerSegment,
    KycStatus,
    RiskRating,
)

if TYPE_CHECKING:
    from app.models.payments import Payment


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_ref: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    legal_name: Mapped[str] = mapped_column(String(200))
    short_name: Mapped[str] = mapped_column(String(80))
    segment: Mapped[CustomerSegment]
    country: Mapped[str] = mapped_column(String(2))
    risk_rating: Mapped[RiskRating]
    kyc_status: Mapped[KycStatus]
    relationship_manager: Mapped[str] = mapped_column(String(128))
    daily_limit_usd: Mapped[Decimal] = mapped_column(MoneyUSD)
    created_at: Mapped[datetime] = mapped_column(default=clock.now)

    accounts: Mapped[list[BankAccount]] = relationship(
        back_populates="customer", order_by="BankAccount.account_ref"
    )
    beneficiaries: Mapped[list[Beneficiary]] = relationship(
        back_populates="customer", order_by="Beneficiary.beneficiary_ref"
    )
    payments: Mapped[list[Payment]] = relationship(back_populates="customer")

    def __repr__(self) -> str:
        return f"Customer(ref={self.customer_ref!r}, name={self.short_name!r})"


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_ref: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    currency: Mapped[Currency]
    account_type: Mapped[AccountType]
    identifier: Mapped[str] = mapped_column(String(64))
    masked_identifier: Mapped[str] = mapped_column(String(64))
    bic: Mapped[str | None] = mapped_column(String(32))
    bank_name: Mapped[str] = mapped_column(String(128))
    available_balance: Mapped[Decimal]
    status: Mapped[AccountStatus] = mapped_column(default=AccountStatus.ACTIVE)

    customer: Mapped[Customer] = relationship(back_populates="accounts")
    payments: Mapped[list[Payment]] = relationship(back_populates="debit_account")

    def __repr__(self) -> str:
        return f"BankAccount(ref={self.account_ref!r}, currency={self.currency.value})"


class Beneficiary(Base):
    __tablename__ = "beneficiaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    beneficiary_ref: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    identifier: Mapped[str] = mapped_column(String(64))
    masked_identifier: Mapped[str] = mapped_column(String(64))
    bic: Mapped[str | None] = mapped_column(String(32))
    bank_name: Mapped[str] = mapped_column(String(128))
    country: Mapped[str] = mapped_column(String(2))
    verification_status: Mapped[BeneficiaryVerificationStatus] = mapped_column(
        default=BeneficiaryVerificationStatus.UNVERIFIED
    )
    registered_at: Mapped[datetime]
    last_used_at: Mapped[datetime | None]

    customer: Mapped[Customer] = relationship(back_populates="beneficiaries")
    payments: Mapped[list[Payment]] = relationship(back_populates="beneficiary")

    def __repr__(self) -> str:
        return f"Beneficiary(ref={self.beneficiary_ref!r}, name={self.name!r})"
