"""REST endpoint for the unified timeline."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query

from app.dependencies import CurrentUser, DBSession
from app.timeline import service
from app.timeline.schemas import TimelineResponse

router = APIRouter(prefix="/api/timeline", tags=["timeline"])


@router.get("/", response_model=TimelineResponse)
async def get_timeline(
    user: CurrentUser,
    db: DBSession,
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    event_type: list[str] | None = Query(default=None),
):
    events, total = await service.collect_timeline(
        db,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
        event_types=event_type,
    )
    return TimelineResponse(total=total, limit=limit, offset=offset, events=events)
