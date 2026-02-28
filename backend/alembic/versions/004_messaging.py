"""004 – Messaging system

Revision ID: 004
Revises: 003
"""

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"


def upgrade() -> None:
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=True),  # NULL = system message
        sa.Column("recipient_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("message_type", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("related_entity", sa.String(50), nullable=True),  # e.g. "expense", "payment"
        sa.Column("related_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_messages_recipient_id", "messages", ["recipient_id"])
    op.create_index("ix_messages_sender_id", "messages", ["sender_id"])
    op.create_index("ix_messages_is_read", "messages", ["is_read"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])

    # Auto-message rules (admin configurable)
    op.create_table(
        "auto_message_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False, unique=True),
        sa.Column("subject_template", sa.String(200), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("send_to", sa.String(30), nullable=False, server_default="affected_user"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("auto_message_rules")
    op.drop_table("messages")

