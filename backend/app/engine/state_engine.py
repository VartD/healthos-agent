"""Derive high-level operating mode from recent events."""

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.models import EventType
from app.schemas import Mode
from app.config import settings


@dataclass(frozen=True)
class EventView:
    event_type: EventType
    value: float | None
    unit: str | None
    note: str | None
    timestamp: datetime
    metadata: dict | None


TZ = ZoneInfo(settings.healthos_timezone)


def _local_date(ts: datetime) -> date:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=TZ)
    return ts.astimezone(TZ).date()


def _today_events(events: list[EventView], today: date) -> list[EventView]:
    return [e for e in events if _local_date(e.timestamp) == today]


def _latest_glucose_today(events: list[EventView], today: date) -> float | None:
    glucose = [e for e in _today_events(events, today) if e.event_type == EventType.glucose and e.value is not None]
    return float(max(glucose, key=lambda e: e.timestamp).value) if glucose else None


def _latest_uric_today(events: list[EventView], today: date) -> float | None:
    values = [e for e in _today_events(events, today) if e.event_type == EventType.uric_acid and e.value is not None]
    return float(max(values, key=lambda e: e.timestamp).value) if values else None


def _sleep_hours_last_night(events: list[EventView], today: date) -> float | None:
    """Most recent sleep event on today or yesterday (MVP)."""
    sleeps = sorted(
        [e for e in events if e.event_type == EventType.sleep and e.value is not None],
        key=lambda e: e.timestamp,
        reverse=True,
    )
    for e in sleeps:
        d = _local_date(e.timestamp)
        if d == today or d == date.fromordinal(today.toordinal() - 1):
            return float(e.value)
    return None


def _has_symptom_today(events: list[EventView], today: date) -> bool:
    return any(e.event_type == EventType.symptom for e in _today_events(events, today))


def _has_workout_today(events: list[EventView], today: date) -> bool:
    return any(e.event_type == EventType.workout for e in _today_events(events, today))


def _user_has_fat_loss_goal(events: list[EventView]) -> bool:
    for e in events:
        meta = e.metadata or {}
        goals = meta.get("goals")
        if isinstance(goals, list) and "fat_loss" in goals:
            return True
        if goals == "fat_loss":
            return True
    return False


def compute_mode(events: list[EventView], *, today: date | None = None) -> Mode:
    today = today or datetime.now(TZ).date()

    g = _latest_glucose_today(events, today)
    if g is not None and g > 7:
        return Mode.STABILIZATION

    u = _latest_uric_today(events, today)
    if u is not None and u > 360:
        return Mode.STABILIZATION

    if _has_workout_today(events, today):
        return Mode.TRAINING

    sleep_h = _sleep_hours_last_night(events, today)
    if sleep_h is not None and sleep_h < 6.5:
        return Mode.RECOVERY

    if _has_symptom_today(events, today):
        return Mode.RECOVERY

    if _user_has_fat_loss_goal(events):
        return Mode.DRY_MODE

    return Mode.NORMAL
