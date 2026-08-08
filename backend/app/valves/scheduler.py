"""Background scheduler for valve schedules.

Designed to run as an ``asyncio`` task started from the FastAPI lifespan.
Triggers schedules at the configured minute and closes valves after the
configured duration. The scheduler is *idempotent* and *purely driven by
the database* – it never holds long-lived in-memory state.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from app.database import async_session_factory
from app.valves import service as valve_service
from app.valves.models import Valve

logger = logging.getLogger("gartenapp.scheduler")

# How often we tick (seconds). The user wants valves polled every minute.
TICK_INTERVAL_SECONDS = 60
# Pending close-tasks keyed by valve_id; used so we can cancel / replace them
_pending_closes: dict[int, asyncio.Task[None]] = {}


async def tick(db_factory) -> None:
    """Run one scheduler pass."""
    weekday_map = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

    async with db_factory() as db:
        schedules = await valve_service.list_active_schedules(db)

    now = datetime.now(UTC)
    current_day = weekday_map[now.weekday()]
    current_time = now.strftime("%H:%M")

    for sched in schedules:
        if current_day not in sched.days_of_week:
            continue
        if sched.start_time != current_time:
            continue
        # De-duplicate: don't fire twice within the same minute
        if sched.last_run_at and (
            now - sched.last_run_at
        ) < timedelta(seconds=TICK_INTERVAL_SECONDS):
            continue

        async with db_factory() as db:
            valve = await valve_service.get_valve(db, sched.valve_id)
            if valve is None or not valve.is_active:
                continue
            from app.valves.schemas import ValveStateCommand

            await valve_service.command_valve(
                db,
                valve,
                ValveStateCommand(
                    new_state="open",
                    duration_seconds=sched.duration_seconds,
                    reason=f"Schedule: {sched.name}",
                ),
                triggered_by=f"schedule:{sched.id}",
                triggered_by_id=None,
            )
            sched.last_run_at = now
            await db.commit()
            logger.info(
                "Schedule %s fired: opened valve %s for %ss",
                sched.name,
                valve.name,
                sched.duration_seconds,
            )


def schedule_close_after(
    db_factory,
    valve: Valve,
    duration_seconds: int,
    triggered_by: str,
) -> None:
    """Spawn (or replace) an asyncio task that closes ``valve`` after
    ``duration_seconds``. We respect ``valve.max_runtime_seconds`` as an
    absolute upper bound.
    """
    loop = asyncio.get_event_loop()
    duration = min(duration_seconds, valve.max_runtime_seconds)

    async def _close() -> None:
        try:
            await asyncio.sleep(duration)
            async with db_factory() as db:
                v = await valve_service.get_valve(db, valve.id)
                if v is None or not v.is_active:
                    return
                if v.desired_state != "open":
                    return
                from app.valves.schemas import ValveStateCommand

                await valve_service.command_valve(
                    db,
                    v,
                    ValveStateCommand(
                        new_state="closed",
                        reason=f"Auto-close after {duration}s ({triggered_by})",
                    ),
                    triggered_by=f"auto_close:{triggered_by}",
                    triggered_by_id=None,
                )
                await db.commit()
                logger.info("Auto-closed valve %s after %ss", v.name, duration)
        except asyncio.CancelledError:
            logger.debug("Auto-close task for valve %s cancelled", valve.id)
            raise

    # Cancel any existing task for this valve
    existing = _pending_closes.get(valve.id)
    if existing and not existing.done():
        existing.cancel()

    _pending_closes[valve.id] = loop.create_task(_close())


async def run_scheduler() -> None:
    """Long-running task: tick every TICK_INTERVAL_SECONDS."""
    logger.info("Valve scheduler started (tick=%ss)", TICK_INTERVAL_SECONDS)
    try:
        while True:
            try:
                await tick(async_session_factory)
            except Exception:
                logger.exception("Scheduler tick failed")
            await asyncio.sleep(TICK_INTERVAL_SECONDS)
    except asyncio.CancelledError:
        logger.info("Valve scheduler stopped")
        raise
