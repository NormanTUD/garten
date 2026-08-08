"""IoT devices, cameras, network allowlist, valves, audit hash chain.

Revision ID: 006
Revises: 005
Create Date: 2026-08-08
"""
from alembic import op
import sqlalchemy as sa


revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── Devices ──────────────────────────────────────────────────
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("device_type", sa.String(50), nullable=False, index=True),
        sa.Column("hardware_id", sa.String(100), nullable=True, index=True),
        sa.Column("api_key_hash", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )

    op.create_table(
        "device_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("event_type", sa.String(50), nullable=False, index=True),
        sa.Column("severity", sa.String(20), nullable=False, server_default="info"),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
    )

    # ─── Cameras ──────────────────────────────────────────────────
    op.create_table(
        "cameras",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("stream_url", sa.String(500), nullable=True),
        sa.Column("snapshot_url", sa.String(500), nullable=True),
        sa.Column("capture_interval_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("retention_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("detect_faces", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "known_persons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("mac_address", sa.String(17), nullable=True, index=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("face_embeddings", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "captured_images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("thumbnail_path", sa.String(500), nullable=True),
        sa.Column("mime_type", sa.String(50), nullable=False, server_default="image/jpeg"),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column("trigger", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("motion_score", sa.Float(), nullable=True),
        sa.Column("weather_temp_c", sa.Float(), nullable=True),
        sa.Column("weather_desc", sa.String(100), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
    )

    op.create_table(
        "face_detections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("image_id", sa.Integer(), sa.ForeignKey("captured_images.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("person_id", sa.Integer(), sa.ForeignKey("known_persons.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("bounding_box", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_unknown", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("embedding", sa.Text(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "camera_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("image_id", sa.Integer(), sa.ForeignKey("captured_images.id", ondelete="SET NULL"), nullable=True),
        sa.Column("alert_type", sa.String(50), nullable=False, index=True),
        sa.Column("severity", sa.String(20), nullable=False, server_default="warning"),
        sa.Column("message", sa.String(500), nullable=False),
        sa.Column("acknowledged_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
    )

    # ─── Network allowlist ────────────────────────────────────────
    op.create_table(
        "network_devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mac_address", sa.String(17), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("device_type", sa.String(30), nullable=False, server_default="unknown"),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("known_person_id", sa.Integer(), sa.ForeignKey("known_persons.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_trusted", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ─── Valves ───────────────────────────────────────────────────
    op.create_table(
        "valves",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("bed_id", sa.Integer(), sa.ForeignKey("beds.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("hardware_id", sa.String(100), nullable=True, index=True),
        sa.Column("gpio_pin", sa.Integer(), nullable=True),
        sa.Column("normally_open", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("max_runtime_seconds", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column("flow_liters_per_minute", sa.Float(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("current_state", sa.String(10), nullable=False, server_default="closed"),
        sa.Column("desired_state", sa.String(10), nullable=False, server_default="closed"),
        sa.Column("state_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "valve_schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("valve_id", sa.Integer(), sa.ForeignKey("valves.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("start_time", sa.String(5), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("days_of_week", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "valve_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("valve_id", sa.Integer(), sa.ForeignKey("valves.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("new_state", sa.String(10), nullable=False),
        sa.Column("triggered_by", sa.String(30), nullable=False),
        sa.Column("triggered_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.String(200), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("water_amount_liters", sa.Float(), nullable=True),
    )

    # ─── Audit hash chain ─────────────────────────────────────────
    op.add_column("audit_logs", sa.Column("prev_hash", sa.String(64), nullable=True))
    op.add_column("audit_logs", sa.Column("entry_hash", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("audit_logs", "entry_hash")
    op.drop_column("audit_logs", "prev_hash")
    op.drop_table("valve_events")
    op.drop_table("valve_schedules")
    op.drop_table("valves")
    op.drop_table("network_devices")
    op.drop_table("camera_alerts")
    op.drop_table("face_detections")
    op.drop_table("captured_images")
    op.drop_table("known_persons")
    op.drop_table("cameras")
    op.drop_table("device_events")
    op.drop_table("devices")
