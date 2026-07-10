from datetime import date, datetime, timedelta, timezone
from statistics import mean
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import EventType, HealthEvent, SleepCheckin, UserProfile, utc_now
from app.security import require_api_key
from app.sleep_schemas import (
    ProfileRead,
    ProfileUpsert,
    SleepCheckinRead,
    SleepCheckinUpsert,
    SleepWeeklySummary,
)


router = APIRouter(tags=["sleep"], dependencies=[Security(require_api_key)])


def _get_or_create_profile(db: Session, user_id: str) -> UserProfile:
    profile = db.get(UserProfile, user_id)
    if profile is None:
        profile = UserProfile(
            user_id=user_id,
            timezone=settings.healthos_timezone,
            sleep_goal_minutes=480,
            reminders_enabled=False,
        )
        db.add(profile)
        db.flush()
    return profile


def _checkin_read(row: SleepCheckin) -> SleepCheckinRead:
    return SleepCheckinRead(
        id=row.id,
        user_id=row.user_id,
        sleep_date=row.sleep_date,
        duration_hours=round(row.duration_minutes / 60, 2),
        quality=row.quality,
        awakenings=row.awakenings,
        energy=row.energy,
        note=row.note,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.put("/profile", response_model=ProfileRead)
def put_profile(payload: ProfileUpsert, db: Session = Depends(get_db)) -> UserProfile:
    profile = db.get(UserProfile, payload.user_id)
    if profile is None:
        profile = UserProfile(user_id=payload.user_id)
        db.add(profile)
    profile.timezone = payload.timezone
    profile.sleep_goal_minutes = payload.sleep_goal_minutes
    profile.morning_reminder = payload.morning_reminder
    profile.evening_reminder = payload.evening_reminder
    profile.reminders_enabled = payload.reminders_enabled
    profile.updated_at = utc_now()
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/profile", response_model=ProfileRead)
def get_profile(
    user_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
) -> UserProfile:
    profile = db.get(UserProfile, user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile not found")
    return profile


@router.put("/sleep/checkin", response_model=SleepCheckinRead)
def put_sleep_checkin(
    payload: SleepCheckinUpsert,
    db: Session = Depends(get_db),
) -> SleepCheckinRead:
    profile = _get_or_create_profile(db, payload.user_id)
    sleep_date = payload.sleep_date or datetime.now(ZoneInfo(profile.timezone)).date()
    duration_minutes = round(payload.duration_hours * 60)

    row = db.scalar(
        select(SleepCheckin).where(
            SleepCheckin.user_id == payload.user_id,
            SleepCheckin.sleep_date == sleep_date,
        )
    )
    event_metadata = {
        "source": "sleep_checkin",
        "sleep_date": sleep_date.isoformat(),
        "quality": payload.quality,
        "awakenings": payload.awakenings,
        "energy": payload.energy,
    }

    if row is None:
        health_event = HealthEvent(
            user_id=payload.user_id,
            timestamp=datetime.now(timezone.utc),
            event_type=EventType.sleep,
            value=duration_minutes / 60,
            unit="h",
            note=payload.note,
            event_metadata=event_metadata,
        )
        db.add(health_event)
        db.flush()
        row = SleepCheckin(
            user_id=payload.user_id,
            health_event_id=health_event.id,
            sleep_date=sleep_date,
            duration_minutes=duration_minutes,
            quality=payload.quality,
            awakenings=payload.awakenings,
            energy=payload.energy,
            note=payload.note,
        )
        db.add(row)
    else:
        health_event = db.get(HealthEvent, row.health_event_id)
        if health_event is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="linked health event is missing",
            )
        health_event.value = duration_minutes / 60
        health_event.note = payload.note
        health_event.event_metadata = event_metadata
        row.duration_minutes = duration_minutes
        row.quality = payload.quality
        row.awakenings = payload.awakenings
        row.energy = payload.energy
        row.note = payload.note
        row.updated_at = utc_now()

    db.commit()
    db.refresh(row)
    return _checkin_read(row)


@router.get("/sleep/checkins", response_model=list[SleepCheckinRead])
def list_sleep_checkins(
    user_id: str = Query(..., min_length=1, max_length=128),
    days: int = Query(default=30, ge=1, le=90),
    db: Session = Depends(get_db),
) -> list[SleepCheckinRead]:
    profile = db.get(UserProfile, user_id)
    timezone_name = profile.timezone if profile is not None else settings.healthos_timezone
    today = datetime.now(ZoneInfo(timezone_name)).date()
    start = today - timedelta(days=days - 1)
    rows = list(
        db.scalars(
            select(SleepCheckin)
            .where(
                SleepCheckin.user_id == user_id,
                SleepCheckin.sleep_date >= start,
                SleepCheckin.sleep_date <= today,
            )
            .order_by(SleepCheckin.sleep_date.desc())
        ).all()
    )
    return [_checkin_read(row) for row in rows]


def choose_next_action(
    *,
    days_logged: int,
    average_duration_minutes: float | None,
    average_quality: float | None,
    sleep_goal_minutes: int,
) -> str:
    if days_logged < 4:
        return "Следующие 7 дней заполните утренний чекин минимум 4 раза."
    if average_duration_minutes is not None and average_duration_minutes < sleep_goal_minutes:
        return "Следующие 7 дней начинайте подготовку ко сну на 15 минут раньше."
    if average_quality is not None and average_quality < 3:
        return "Следующие 7 дней сохраняйте постоянное время подъёма и отмечайте главный нарушитель сна."
    return "Сохраните текущий режим ещё на 7 дней и продолжайте ежедневные отметки."


@router.get("/sleep/weekly", response_model=SleepWeeklySummary)
def weekly_sleep_summary(
    user_id: str = Query(..., min_length=1, max_length=128),
    period_end: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> SleepWeeklySummary:
    profile = db.get(UserProfile, user_id)
    timezone_name = profile.timezone if profile is not None else settings.healthos_timezone
    sleep_goal_minutes = profile.sleep_goal_minutes if profile is not None else 480
    end = period_end or datetime.now(ZoneInfo(timezone_name)).date()
    start = end - timedelta(days=6)
    rows = list(
        db.scalars(
            select(SleepCheckin)
            .where(
                SleepCheckin.user_id == user_id,
                SleepCheckin.sleep_date >= start,
                SleepCheckin.sleep_date <= end,
            )
            .order_by(SleepCheckin.sleep_date)
        ).all()
    )
    durations = [row.duration_minutes for row in rows]
    qualities = [row.quality for row in rows]
    awakenings = [row.awakenings for row in rows]
    energies = [row.energy for row in rows]
    average_duration_minutes = mean(durations) if durations else None
    average_quality = mean(qualities) if qualities else None

    return SleepWeeklySummary(
        user_id=user_id,
        period_start=start,
        period_end=end,
        days_logged=len(rows),
        average_duration_hours=(
            round(average_duration_minutes / 60, 2)
            if average_duration_minutes is not None
            else None
        ),
        average_quality=round(average_quality, 2) if average_quality is not None else None,
        average_awakenings=round(mean(awakenings), 2) if awakenings else None,
        average_energy=round(mean(energies), 2) if energies else None,
        goal_met_days=sum(
            1 for row in rows if row.duration_minutes >= sleep_goal_minutes
        ),
        sleep_goal_hours=round(sleep_goal_minutes / 60, 2),
        next_best_action=choose_next_action(
            days_logged=len(rows),
            average_duration_minutes=average_duration_minutes,
            average_quality=average_quality,
            sleep_goal_minutes=sleep_goal_minutes,
        ),
    )
