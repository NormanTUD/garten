from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ExpenseCategory(Base):
    __tablename__ = "expense_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RecurringCost(Base):
    """Monthly or yearly base costs with validity period.

    Example: Strom 30€/Monat from 2025-01-01 to 2025-12-31,
             Strom 40€/Monat from 2026-01-01 to None (ongoing).
    """
    __tablename__ = "recurring_costs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("expense_categories.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    interval: Mapped[str] = mapped_column(String(20), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    category: Mapped["ExpenseCategory | None"] = relationship(lazy="selectin")


class GardenExpense(Base):
    __tablename__ = "garden_expenses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("expense_categories.id", ondelete="SET NULL"), nullable=True
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    receipt_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ocr_raw_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(lazy="selectin")  # noqa: F821
    category: Mapped["ExpenseCategory | None"] = relationship(lazy="selectin")


class MemberPayment(Base):
    __tablename__ = "member_payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    for_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    receipt_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    confirmed_by_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(foreign_keys=[user_id], lazy="selectin")  # noqa: F821
    for_user: Mapped["User | None"] = relationship(foreign_keys=[for_user_id], lazy="selectin")  # noqa: F821

class StandingOrder(Base):
    """Recurring payment commitment from a member (e.g. SEPA direct debit).

    Example: "I pay 50€/month via SEPA starting 2026-01-01"
    Each month is auto-counted as paid unless an admin marks it as skipped.
    """
    __tablename__ = "standing_orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(lazy="selectin")  # noqa: F821
    skips: Mapped[list["StandingOrderSkip"]] = relationship(
        back_populates="standing_order", lazy="selectin", cascade="all, delete-orphan"
    )


class StandingOrderSkip(Base):
    """Marks a month where a standing order was NOT paid."""
    __tablename__ = "standing_order_skips"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    standing_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("standing_orders.id", ondelete="CASCADE"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    standing_order: Mapped["StandingOrder"] = relationship(back_populates="skips")

