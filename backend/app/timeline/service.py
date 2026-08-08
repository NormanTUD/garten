"""Unified timeline across all garden-app modules.

We query every relevant table, normalize the rows into :class:`TimelineEvent`
and merge-sort them by timestamp. The result is a single chronologically
ordered feed – ideal for a "Was ist passiert?" view.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.models import User
from app.cameras.models import CameraAlert, CapturedImage
from app.duty.models import GardenDutyLog
from app.finance.models import GardenExpense, MemberPayment
from app.harvest.models import Harvest
from app.messaging.models import Message
from app.shopping.models import ShoppingItem
from app.timeline.schemas import TimelineEvent
from app.valves.models import ValveEvent
from app.watering.models import FertilizingEvent, WateringEvent

logger = logging.getLogger("gartenapp.timeline")


ICON_MAP: dict[str, tuple[str, str]] = {
    "harvest": ("mdi-basket", "green"),
    "watering": ("mdi-water", "blue"),
    "fertilizing": ("mdi-flask", "amber"),
    "expense": ("mdi-cash-minus", "red"),
    "payment": ("mdi-cash-plus", "green"),
    "standing_order": ("mdi-bank-transfer", "blue"),
    "duty_log": ("mdi-shovel", "brown"),
    "duty_confirmed": ("mdi-check-circle", "green"),
    "message": ("mdi-email", "blue"),
    "shopping_added": ("mdi-cart-plus", "orange"),
    "shopping_purchased": ("mdi-cart-check", "green"),
    "image_captured": ("mdi-camera", "blue"),
    "camera_alert": ("mdi-alert", "red"),
    "valve_opened": ("mdi-water-pump", "blue"),
    "valve_closed": ("mdi-water-off", "grey"),
    "device_event": ("mdi-chip", "blue"),
}


def _icon(event_type: str) -> tuple[str | None, str | None]:
    return ICON_MAP.get(event_type, (None, None))


def _user_name(user: User | None) -> str | None:
    return user.display_name if user else None


async def _collect_harvests(
    db: AsyncSession, date_from: datetime | None, date_to: datetime | None
) -> list[TimelineEvent]:
    stmt = select(Harvest).options(selectinload(Harvest.user))
    if date_from:
        stmt = stmt.where(Harvest.harvest_date >= date_from.date())
    if date_to:
        stmt = stmt.where(Harvest.harvest_date <= date_to.date())
    rows = list((await db.execute(stmt)).scalars().all())
    return [
        TimelineEvent(
            id=f"harvest:{h.id}",
            event_type="harvest",
            occurred_at=datetime.combine(h.harvest_date, datetime.min.time(), tzinfo=UTC),
            actor_id=h.user_id,
            actor_name=_user_name(h.user),
            title=f"Ernte: {h.amount:g} {h.unit or ''}".strip(),
            summary=h.notes or (h.plant.name if h.plant else ""),
            icon=_icon("harvest")[0],
            color=_icon("harvest")[1],
            extra={"harvest_id": h.id},
        )
        for h in rows
    ]


async def _collect_waterings(
    db: AsyncSession, date_from: datetime | None, date_to: datetime | None
) -> list[TimelineEvent]:
    stmt = select(WateringEvent).options(selectinload(WateringEvent.user))
    if date_from:
        stmt = stmt.where(WateringEvent.started_at >= date_from)
    if date_to:
        stmt = stmt.where(WateringEvent.started_at <= date_to)
    rows = list((await db.execute(stmt)).scalars().all())
    return [
        TimelineEvent(
            id=f"watering:{w.id}",
            event_type="watering",
            occurred_at=w.started_at,
            actor_id=w.user_id,
            actor_name=_user_name(w.user),
            title="Bewässerung",
            summary=(
                f"{w.water_amount_liters:g} L über {w.duration_minutes:g} min"
                if w.water_amount_liters and w.duration_minutes
                else (w.notes or "")
            ),
            icon=_icon("watering")[0],
            color=_icon("watering")[1],
            extra={"watering_id": w.id},
        )
        for w in rows
    ]


async def _collect_fertilizings(
    db: AsyncSession, date_from: datetime | None, date_to: datetime | None
) -> list[TimelineEvent]:
    stmt = select(FertilizingEvent)
    if date_from:
        stmt = stmt.where(FertilizingEvent.event_date >= date_from.date())
    if date_to:
        stmt = stmt.where(FertilizingEvent.event_date <= date_to.date())
    rows = list((await db.execute(stmt)).scalars().all())
    return [
        TimelineEvent(
            id=f"fertilizing:{f.id}",
            event_type="fertilizing",
            occurred_at=datetime.combine(f.event_date, datetime.min.time(), tzinfo=UTC),
            title=f"Düngung: {f.fertilizer_type}",
            summary=(
                f"{f.amount:g} {f.unit or ''}".strip()
                if f.amount is not None
                else ""
            ),
            icon=_icon("fertilizing")[0],
            color=_icon("fertilizing")[1],
            extra={"fertilizing_id": f.id},
        )
        for f in rows
    ]


async def _collect_expenses(
    db: AsyncSession, date_from: datetime | None, date_to: datetime | None
) -> list[TimelineEvent]:
    stmt = select(GardenExpense).options(selectinload(GardenExpense.user))
    if date_from:
        stmt = stmt.where(GardenExpense.expense_date >= date_from.date())
    if date_to:
        stmt = stmt.where(GardenExpense.expense_date <= date_to.date())
    rows = list((await db.execute(stmt)).scalars().all())
    return [
        TimelineEvent(
            id=f"expense:{e.id}",
            event_type="expense",
            occurred_at=datetime.combine(e.expense_date, datetime.min.time(), tzinfo=UTC),
            actor_id=e.user_id,
            actor_name=_user_name(e.user),
            title=f"Ausgabe: {e.amount_cents / 100:.2f} €",
            summary=e.description,
            icon=_icon("expense")[0],
            color=_icon("expense")[1],
            extra={"expense_id": e.id, "is_shared": e.is_shared, "confirmed": e.confirmed_by_admin},
        )
        for e in rows
    ]


async def _collect_payments(
    db: AsyncSession, date_from: datetime | None, date_to: datetime | None
) -> list[TimelineEvent]:
    stmt = select(MemberPayment).options(selectinload(MemberPayment.user))
    if date_from:
        stmt = stmt.where(MemberPayment.payment_date >= date_from.date())
    if date_to:
        stmt = stmt.where(MemberPayment.payment_date <= date_to.date())
    rows = list((await db.execute(stmt)).scalars().all())
    return [
        TimelineEvent(
            id=f"payment:{p.id}",
            event_type="payment",
            occurred_at=datetime.combine(p.payment_date, datetime.min.time(), tzinfo=UTC),
            actor_id=p.user_id,
            actor_name=_user_name(p.user),
            title=f"Einzahlung: {p.amount_cents / 100:.2f} €",
            summary=p.description or "",
            icon=_icon("payment")[0],
            color=_icon("payment")[1],
            extra={"payment_id": p.id, "payment_type": p.payment_type},
        )
        for p in rows
    ]


async def _collect_duty_logs(
    db: AsyncSession, date_from: datetime | None, date_to: datetime | None
) -> list[TimelineEvent]:
    stmt = select(GardenDutyLog).options(selectinload(GardenDutyLog.user))
    if date_from:
        stmt = stmt.where(GardenDutyLog.date >= date_from.date())
    if date_to:
        stmt = stmt.where(GardenDutyLog.date <= date_to.date())
    rows = list((await db.execute(stmt)).scalars().all())
    return [
        TimelineEvent(
            id=f"duty_log:{d.id}",
            event_type="duty_confirmed" if d.confirmed else "duty_log",
            occurred_at=datetime.combine(d.date, datetime.min.time(), tzinfo=UTC),
            actor_id=d.user_id,
            actor_name=_user_name(d.user),
            title=f"Gartenstunden: {d.hours:g} h",
            summary=d.description or "",
            icon=_icon("duty_confirmed" if d.confirmed else "duty_log")[0],
            color=_icon("duty_confirmed" if d.confirmed else "duty_log")[1],
            extra={"duty_log_id": d.id, "confirmed": d.confirmed},
        )
        for d in rows
    ]


async def _collect_messages(
    db: AsyncSession, date_from: datetime | None, date_to: datetime | None
) -> list[TimelineEvent]:
    stmt = select(Message).options(
        selectinload(Message.sender), selectinload(Message.recipient)
    )
    if date_from:
        stmt = stmt.where(Message.created_at >= date_from)
    if date_to:
        stmt = stmt.where(Message.created_at <= date_to)
    rows = list((await db.execute(stmt)).scalars().all())
    return [
        TimelineEvent(
            id=f"message:{m.id}",
            event_type="message",
            occurred_at=m.created_at,
            actor_id=m.sender_id,
            actor_name=_user_name(m.sender),
            title=m.subject,
            summary=m.body[:200],
            icon=_icon("message")[0],
            color=_icon("message")[1],
            extra={"message_id": m.id, "recipient_id": m.recipient_id},
        )
        for m in rows
        if not m.message_type.startswith("auto:")  # keep user-driven only
    ]


async def _collect_shopping(
    db: AsyncSession, date_from: datetime | None, date_to: datetime | None
) -> list[TimelineEvent]:
    stmt = select(ShoppingItem).options(selectinload(ShoppingItem.added_by))
    rows = list((await db.execute(stmt)).scalars().all())
    events: list[TimelineEvent] = []
    for item in rows:
        if date_from and item.created_at < date_from:
            continue
        if date_to and item.created_at > date_to:
            continue
        events.append(
            TimelineEvent(
                id=f"shopping:{item.id}",
                event_type="shopping_added",
                occurred_at=item.created_at,
                actor_id=item.added_by_id,
                actor_name=_user_name(item.added_by),
                title=f"Einkaufsliste: {item.title}",
                summary=item.notes or "",
                icon=_icon("shopping_added")[0],
                color=_icon("shopping_added")[1],
                extra={"shopping_id": item.id},
            )
        )
        if item.purchased and item.purchased_at:
            if date_from and item.purchased_at < date_from:
                continue
            if date_to and item.purchased_at > date_to:
                continue
            events.append(
                TimelineEvent(
                    id=f"shopping_purchased:{item.id}",
                    event_type="shopping_purchased",
                    occurred_at=item.purchased_at,
                    actor_id=item.purchased_by_id,
                    actor_name=_user_name(item.purchased_by),
                    title=f"Gekauft: {item.title}",
                    summary=(
                        f"{item.cost_cents / 100:.2f} €" if item.cost_cents else ""
                    ),
                    icon=_icon("shopping_purchased")[0],
                    color=_icon("shopping_purchased")[1],
                    extra={"shopping_id": item.id},
                )
            )
    return events


async def _collect_images(
    db: AsyncSession, date_from: datetime | None, date_to: datetime | None
) -> list[TimelineEvent]:
    stmt = select(CapturedImage)
    if date_from:
        stmt = stmt.where(CapturedImage.captured_at >= date_from)
    if date_to:
        stmt = stmt.where(CapturedImage.captured_at <= date_to)
    rows = list((await db.execute(stmt)).scalars().all())
    return [
        TimelineEvent(
            id=f"image:{img.id}",
            event_type="image_captured",
            occurred_at=img.captured_at,
            title="Kamera-Snapshot",
            summary=img.trigger or "",
            icon=_icon("image_captured")[0],
            color=_icon("image_captured")[1],
            extra={"image_id": img.id, "camera_id": img.camera_id},
        )
        for img in rows
    ]


async def _collect_camera_alerts(
    db: AsyncSession, date_from: datetime | None, date_to: datetime | None
) -> list[TimelineEvent]:
    stmt = select(CameraAlert)
    if date_from:
        stmt = stmt.where(CameraAlert.created_at >= date_from)
    if date_to:
        stmt = stmt.where(CameraAlert.created_at <= date_to)
    rows = list((await db.execute(stmt)).scalars().all())
    return [
        TimelineEvent(
            id=f"alert:{a.id}",
            event_type="camera_alert",
            occurred_at=a.created_at,
            title=f"Alarm: {a.alert_type}",
            summary=a.message,
            icon=_icon("camera_alert")[0],
            color=_icon("camera_alert")[1],
            extra={"alert_id": a.id, "camera_id": a.camera_id},
        )
        for a in rows
    ]


async def _collect_valve_events(
    db: AsyncSession, date_from: datetime | None, date_to: datetime | None
) -> list[TimelineEvent]:
    stmt = select(ValveEvent)
    if date_from:
        stmt = stmt.where(ValveEvent.opened_at >= date_from)
    if date_to:
        stmt = stmt.where(ValveEvent.opened_at <= date_to)
    rows = list((await db.execute(stmt)).scalars().all())
    return [
        TimelineEvent(
            id=f"valve:{v.id}",
            event_type=("valve_opened" if v.new_state == "open" else "valve_closed"),
            occurred_at=v.opened_at,
            title=f"Ventil {v.new_state}",
            summary=v.reason or v.triggered_by,
            icon=_icon("valve_opened" if v.new_state == "open" else "valve_closed")[0],
            color=_icon("valve_opened" if v.new_state == "open" else "valve_closed")[1],
            extra={"valve_id": v.valve_id, "triggered_by": v.triggered_by},
        )
        for v in rows
    ]


_COLLECTORS = [
    _collect_harvests,
    _collect_waterings,
    _collect_fertilizings,
    _collect_expenses,
    _collect_payments,
    _collect_duty_logs,
    _collect_messages,
    _collect_shopping,
    _collect_images,
    _collect_camera_alerts,
    _collect_valve_events,
]


async def collect_timeline(
    db: AsyncSession,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 200,
    offset: int = 0,
    event_types: list[str] | None = None,
) -> tuple[list[TimelineEvent], int]:
    events: list[TimelineEvent] = []
    for collector in _COLLECTORS:
        try:
            events.extend(await collector(db, date_from, date_to))
        except Exception:
            logger.exception("Timeline collector %s failed", collector.__name__)

    if event_types:
        events = [e for e in events if e.event_type in event_types]

    events.sort(key=lambda e: e.occurred_at, reverse=True)
    total = len(events)
    return events[offset : offset + limit], total
