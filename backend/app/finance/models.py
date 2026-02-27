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
    """Monthly or yearly base costs (rent, water, insurance, etc.)."""
    __tablename__ = "recurring_costs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("expense_categories.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    interval: Mapped[str] = mapped_column(String(20), nullable=False)  # monthly, yearly
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    category: Mapped["ExpenseCategory | None"] = relationship(lazy="selectin")


class GardenExpense(Base):
    """One-time expenses (tools, seeds, materials, etc.)."""
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
    receipt_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ocr_raw_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(lazy="selectin")  # noqa: F821
    category: Mapped["ExpenseCategory | None"] = relationship(lazy="selectin")


class MemberPayment(Base):
    """Payments from members into the garden fund."""
    __tablename__ = "member_payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_type: Mapped[str] = mapped_column(String(20), nullable=False)  # cash, transfer, material
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    receipt_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    confirmed_by_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(lazy="selectin")  # noqa: F821

