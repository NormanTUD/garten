"""Finance tables: expense_categories, garden_expenses, member_payments

Revision ID: 003
Revises: 002
Create Date: 2026-02-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Expense categories (dynamic, user-created)
    op.create_table(
        "expense_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_expense_categories_name", "expense_categories", ["name"], unique=True)

    # Recurring cost templates (monthly/yearly base costs)
    op.create_table(
        "recurring_costs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("interval", sa.String(20), nullable=False),  # monthly, yearly
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),  # NULL = unbegrenzt gültig
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["category_id"], ["expense_categories.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_recurring_costs_valid_from", "recurring_costs", ["valid_from"])


    # Garden expenses (one-time costs that hit the garden account)
    op.create_table(
        "garden_expenses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("receipt_image_path", sa.String(500), nullable=True),
        sa.Column("ocr_raw_result", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["expense_categories.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_garden_expenses_user_id", "garden_expenses", ["user_id"])
    op.create_index("ix_garden_expenses_expense_date", "garden_expenses", ["expense_date"])

    # Member payments into the garden fund
    op.create_table(
        "member_payments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("for_user_id", sa.Integer(), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("payment_type", sa.String(20), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("receipt_image_path", sa.String(500), nullable=True),
        sa.Column("confirmed_by_admin", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["for_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_member_payments_user_id", "member_payments", ["user_id"])
    op.create_index("ix_member_payments_for_user_id", "member_payments", ["for_user_id"])
    op.create_index("ix_member_payments_payment_date", "member_payments", ["payment_date"])

    # Standing orders (recurring payments from members, e.g. SEPA direct debit)
    op.create_table(
        "standing_orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_standing_orders_user_id", "standing_orders", ["user_id"])

    # Skipped months for standing orders (admin marks "not paid this month")
    op.create_table(
        "standing_order_skips",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("standing_order_id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["standing_order_id"], ["standing_orders.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("standing_order_id", "year", "month", name="uq_skip_order_month"),
    )

def downgrade() -> None:
    op.drop_table("standing_order_skips")
    op.drop_table("standing_orders")
    op.drop_table("member_payments")
    op.drop_table("garden_expenses")
    op.drop_table("recurring_costs")
    op.drop_table("expense_categories")
