from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import HealthEvent
from app.schemas import AnalysisResponse, EventCreate, EventRead
from app.analysis import analyze_user

router = APIRouter(tags=["events"])


@router.post("/events", response_model=EventRead)
def post_event(payload: EventCreate, db: Session = Depends(get_db)) -> HealthEvent:
    ts = payload.timestamp or datetime.now(timezone.utc)
    row = HealthEvent(
        user_id=payload.user_id,
        timestamp=ts,
        event_type=payload.event_type,
        value=payload.value,
        unit=payload.unit,
        note=payload.note,
        event_metadata=payload.metadata,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/events", response_model=list[EventRead])
def list_events(
    user_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[HealthEvent]:
    stmt = select(HealthEvent)
    if user_id is not None:
        stmt = stmt.where(HealthEvent.user_id == user_id)
    stmt = stmt.order_by(HealthEvent.timestamp.desc()).limit(limit)
    return list(db.scalars(stmt).all())


@router.get("/analyze", response_model=AnalysisResponse)
def analyze(user_id: str = Query(..., min_length=1), db: Session = Depends(get_db)) -> AnalysisResponse:
    return analyze_user(db, user_id)
