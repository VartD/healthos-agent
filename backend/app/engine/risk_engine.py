"""Risk flags from event combinations (informational, not diagnosis)."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.engine.state_engine import EventView, _local_date, _today_events
from app.models import EventType
from app.config import settings

TZ = ZoneInfo(settings.healthos_timezone)


MEAT_KEYWORDS = ("мясо", "стейк", "биф", "говяд", "свинин", "куриц", "рыба", "протеин", "protein", "steak", "meat")


def _water_ml_today(events: list[EventView], today: date) -> float:
    total = 0.0
    for e in _today_events(events, today):
        if e.event_type != EventType.water or e.value is None:
            continue
        unit = getattr(e, "unit", None)
        raw = float(e.value)
        norm = unit.lower() if isinstance(unit, str) else None
        if norm in ("l", "liter", "л"):
            ml = raw * 1000
        elif norm is None or norm == "ml" or norm == "":
            ml = raw
        else:
            ml = raw * 1000
        total += ml
    return total


def _has_coffee_today(events: list[EventView], today: date) -> bool:
    return any(e.event_type == EventType.coffee for e in _today_events(events, today))


def _has_sauna_today(events: list[EventView], today: date) -> bool:
    return any(e.event_type == EventType.sauna for e in _today_events(events, today))


def _has_workout_today(events: list[EventView], today: date) -> bool:
    return any(e.event_type == EventType.workout for e in _today_events(events, today))


def _food_notes_today(events: list[EventView], today: date) -> str:
    parts: list[str] = []
    for e in _today_events(events, today):
        if e.event_type == EventType.food and e.note:
            parts.append(e.note.lower())
    return " ".join(parts)


def _salt_mentioned_today(events: list[EventView], today: date) -> bool:
    blob = _food_notes_today(events, today)
    return any(k in blob for k in ("соль", "солё", "солен", "salt", "сыр", "закуск"))


def _protein_meat_today(events: list[EventView], today: date) -> bool:
    blob = _food_notes_today(events, today)
    return any(k in blob for k in MEAT_KEYWORDS)


def _latest_glucose_today(events: list[EventView], today: date) -> float | None:
    glucose = [e for e in _today_events(events, today) if e.event_type == EventType.glucose and e.value is not None]
    return float(max(glucose, key=lambda e: e.timestamp).value) if glucose else None


def _latest_uric_today(events: list[EventView], today: date) -> float | None:
    values = [e for e in _today_events(events, today) if e.event_type == EventType.uric_acid and e.value is not None]
    return float(max(values, key=lambda e: e.timestamp).value) if values else None


def _latest_blood_pressure_today(
    events: list[EventView], today: date
) -> tuple[float, float] | None:
    values = [
        e
        for e in _today_events(events, today)
        if e.event_type == EventType.blood_pressure and e.value is not None
    ]
    if not values:
        return None
    latest = max(values, key=lambda e: e.timestamp)
    metadata = latest.metadata or {}
    systolic = float(metadata.get("systolic", latest.value))
    diastolic = metadata.get("diastolic")
    if not isinstance(diastolic, (int, float)):
        return None
    return systolic, float(diastolic)


def _sleep_hours_recent(events: list[EventView], today: date) -> float | None:
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


LOW_WATER_ML = 1200.0


def detect_risks(events: list[EventView], *, today: date | None = None) -> list[str]:
    today = today or datetime.now(TZ).date()
    risks: list[str] = []

    water_ml_today = 0.0
    coffee_ml_today = 0.0
    coffee_today = False
    coffee_after_16_moscow = False
    for e in _today_events(events, today):
        event_type = getattr(e, "event_type", "")
        type_str = event_type.value if hasattr(event_type, "value") else str(event_type or "")
        value = getattr(e, "value", 0) or 0
        unit = e.unit
        timestamp = getattr(e, "timestamp", None)
        try:
            val_f = float(value)
        except (TypeError, ValueError):
            val_f = None
        if type_str == "water" and val_f is not None:
            if unit and isinstance(unit, str) and unit.lower() in ("l", "liter", "литр", "л"):
                water_ml_today += val_f * 1000
            else:
                water_ml_today += val_f
        if type_str == "coffee":
            coffee_today = True
            if val_f is not None:
                if unit and isinstance(unit, str) and unit.lower() in ("l", "liter", "литр", "л"):
                    coffee_ml_today += val_f * 1000
                else:
                    coffee_ml_today += val_f
            if timestamp is not None:
                ts = timestamp
                if getattr(ts, "tzinfo", None) is None:
                    ts = ts.replace(tzinfo=TZ)
                else:
                    ts = ts.astimezone(TZ)
                if ts.hour >= 16:
                    coffee_after_16_moscow = True

    water_ml = _water_ml_today(events, today)
    low_water = water_ml < LOW_WATER_ML

    if _has_coffee_today(events, today) and low_water:
        risks.append("coffee_low_water")

    if _salt_mentioned_today(events, today) and low_water:
        risks.append("salt_low_water")

    if _has_workout_today(events, today) and _has_sauna_today(events, today) and low_water:
        risks.append("workout_sauna_low_water")

    uric = _latest_uric_today(events, today)
    if uric is not None and uric > 360 and _protein_meat_today(events, today):
        risks.append("uric_high_protein")

    sleep_h = _sleep_hours_recent(events, today)
    if sleep_h is not None and sleep_h < 6.5 and _has_coffee_today(events, today):
        risks.append("poor_sleep_coffee")

    g = _latest_glucose_today(events, today)
    if g is not None and g > 8:
        risks.append("glucose_high")

    if uric is not None and uric > 360:
        risks.append("uric_high")

    blood_pressure = _latest_blood_pressure_today(events, today)
    if blood_pressure is not None:
        systolic, diastolic = blood_pressure
        if systolic >= 180 or diastolic >= 120:
            risks.insert(0, "blood_pressure_critical")

    if coffee_after_16_moscow:
        risks.append("coffee_late")

    if coffee_today and water_ml_today < coffee_ml_today * 2:
        risks.append("coffee_water_compensation")

    return risks
