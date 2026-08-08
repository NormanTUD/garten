"""Pydantic schemas for the unified timeline view."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

TimelineEventType = Literal[
    "harvest",
    "watering",
    "fertilizing",
    "expense",
    "payment",
    "standing_order",
    "duty_log",
    "duty_confirmed",
    "message",
    "shopping_added",
    "shopping_purchased",
    "image_captured",
    "camera_alert",
    "valve_opened",
    "valve_closed",
    "device_event",
    "user_created",
    "audit",
]


class TimelineEvent(BaseModel):
    """A single, normalized entry in the garden timeline."""

    id: str = Field(..., description="Stable composite id, e.g. 'expense:42'")
    event_type: TimelineEventType
    occurred_at: datetime
    actor_id: int | None = None
    actor_name: str | None = None
    title: str
    summary: str
    icon: str | None = None
    color: str | None = None
    extra: dict[str, Any] | None = None


class TimelineResponse(BaseModel):
    total: int
    limit: int
    offset: int
    events: list[TimelineEvent]
