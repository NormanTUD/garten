"""Finance tables: expense_categories, expenses, expense_splits, payments

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
    # Expense categories
    op.create_table(
        "expense_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_expense_categories_name", "expense_categories", ["name"], unique=True)

    # Expenses
    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("is_recurring", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("recurrence_interval", sa.String(20), nullable=True),
        sa.Column("receipt_image_path", sa.String(500), nullable=True),
        sa.Column("ocr_raw_result", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["expense_categories.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_expenses_user_id", "expenses", ["user_id"])
    op.create_index("ix_expenses_category_id", "expenses", ["category_id"])
    op.create_index("ix_expenses_expense_date", "expenses", ["expense_date"])

    # Expense splits
    op.create_table(
        "expense_splits",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("expense_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("share_amount_cents", sa.Integer(), nullable=False),
        sa.Column("is_settled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["expense_id"], ["expenses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_expense_splits_expense_id", "expense_splits", ["expense_id"])
    op.create_index("ix_expense_splits_user_id", "expense_splits", ["user_id"])

    # Payments
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("from_user_id", sa.Integer(), nullable=False),
        sa.Column("to_user_id", sa.Integer(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("method", sa.String(20), nullable=False, server_default="cash"),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("confirmed_by_admin", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["from_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_payments_from_user_id", "payments", ["from_user_id"])
    op.create_index("ix_payments_to_user_id", "payments", ["to_user_id"])
    op.create_index("ix_payments_payment_date", "payments", ["payment_date"])


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_table("expense_splits")
    op.drop_table("expenses")
    op.drop_table("expense_categories")

