from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Security
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import HealthEvent
from app.schemas import AnalysisResponse, EventBatchCreate, EventCreate, EventRead
from app.analysis import analyze_user
from app.security import require_api_key

router = APIRouter(tags=["events"], dependencies=[Security(require_api_key)])


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


@router.post("/events/batch", response_model=list[EventRead])
def post_event_batch(
    payload: EventBatchCreate, db: Session = Depends(get_db)
) -> list[HealthEvent]:
    now = datetime.now(timezone.utc)
    rows = [
        HealthEvent(
            user_id=event.user_id,
            timestamp=event.timestamp or now,
            event_type=event.event_type,
            value=event.value,
            unit=event.unit,
            note=event.note,
            event_metadata=event.metadata,
        )
        for event in payload.events
    ]
    db.add_all(rows)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


@router.get("/events", response_model=list[EventRead])
def list_events(
    user_id: str = Query(..., min_length=1, max_length=128),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[HealthEvent]:
    stmt = select(HealthEvent).where(HealthEvent.user_id == user_id)
    stmt = stmt.order_by(HealthEvent.timestamp.desc()).limit(limit)
    return list(db.scalars(stmt).all())


@router.get("/analyze", response_model=AnalysisResponse)
def analyze(user_id: str = Query(..., min_length=1), db: Session = Depends(get_db)) -> AnalysisResponse:
    return analyze_user(db, user_id)
