"""Harvest, WateringEvent, FertilizingEvent tables

Revision ID: 002
Revises: 001
Create Date: 2026-02-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Harvests
    op.create_table(
        "harvests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bed_id", sa.Integer(), nullable=True),
        sa.Column("plant_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("quality_rating", sa.Integer(), nullable=True),
        sa.Column("harvest_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bed_id"], ["beds.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_harvests_user_id", "harvests", ["user_id"])
    op.create_index("ix_harvests_bed_id", "harvests", ["bed_id"])
    op.create_index("ix_harvests_plant_id", "harvests", ["plant_id"])
    op.create_index("ix_harvests_harvest_date", "harvests", ["harvest_date"])

    # Watering events
    op.create_table(
        "watering_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bed_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("water_amount_liters", sa.Float(), nullable=True),
        sa.Column("method", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("weather_temp_c", sa.Float(), nullable=True),
        sa.Column("weather_humidity_pct", sa.Float(), nullable=True),
        sa.Column("weather_rain_mm", sa.Float(), nullable=True),
        sa.Column("weather_description", sa.String(200), nullable=True),
        sa.Column("soil_moisture_before", sa.Float(), nullable=True),
        sa.Column("soil_moisture_after", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bed_id"], ["beds.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_watering_events_user_id", "watering_events", ["user_id"])
    op.create_index("ix_watering_events_bed_id", "watering_events", ["bed_id"])
    op.create_index("ix_watering_events_started_at", "watering_events", ["started_at"])

    # Fertilizing events
    op.create_table(
        "fertilizing_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bed_id", sa.Integer(), nullable=True),
        sa.Column("fertilizer_type", sa.String(100), nullable=False),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bed_id"], ["beds.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_fertilizing_events_user_id", "fertilizing_events", ["user_id"])
    op.create_index("ix_fertilizing_events_bed_id", "fertilizing_events", ["bed_id"])
    op.create_index("ix_fertilizing_events_event_date", "fertilizing_events", ["event_date"])


def downgrade() -> None:
    op.drop_table("fertilizing_events")
    op.drop_table("watering_events")
    op.drop_table("harvests")

