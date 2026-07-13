from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.command_engine import build_commands
from app.engine.prediction_engine import build_prediction, predict_consequences, system_effect_lines
from app.engine.risk_engine import detect_risks
from app.engine.state_engine import EventView, compute_mode
from app.models import EventType, HealthEvent
from app.schemas import AnalysisResponse, Mode


def _to_views(rows: list[HealthEvent]) -> list[EventView]:
    return [
        EventView(
            event_type=r.event_type,
            value=r.value,
            unit=r.unit,
            note=r.note,
            timestamp=r.timestamp,
            metadata=r.event_metadata,
        )
        for r in rows
    ]


RISK_LABEL_RU: dict[str, str] = {
    "coffee_low_water": "Кофе при недостатке воды",
    "salt_low_water": "Много соли при недостатке воды",
    "workout_sauna_low_water": "Тренировка и сауна при недостатке воды",
    "uric_high_protein": "Высокая мочевая кислота и белок/мясо",
    "poor_sleep_coffee": "Недосып и кофе",
    "glucose_high": "Глюкоза выше 8",
    "uric_high": "Мочевая кислота выше 360",
    "coffee_late": "Кофе после 16:00",
    "coffee_water_compensation": "Недостаточно воды относительно объёма кофе",
}


MODE_LABEL_RU: dict[Mode, str] = {
    Mode.STABILIZATION: "СТАБИЛИЗАЦИЯ",
    Mode.TRAINING: "ТРЕНИРОВКА",
    Mode.RECOVERY: "ВОССТАНОВЛЕНИЕ",
    Mode.DRY_MODE: "СУХОЙ РЕЖИМ",
    Mode.NORMAL: "НОРМА",
}


SEVERE_SYMPTOM_MARKERS = (
    "одышк",
    "боль в груди",
    "жар",
    "лихорадк",
    "потеря сознания",
    "обморок",
    "кровь",
    "инфаркт",
    "инсульт",
    "суицид",
)


def _severe_symptom(events: list[HealthEvent], *, window_hours: int = 24) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    for r in events:
        if r.event_type != EventType.symptom or not r.note:
            continue
        timestamp = r.timestamp
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        if timestamp < cutoff:
            continue
        low = r.note.lower()
        if any(m in low for m in SEVERE_SYMPTOM_MARKERS):
            return True
    return False


def analyze_user(db: Session, user_id: str, *, limit_events: int = 500) -> AnalysisResponse:
    stmt = (
        select(HealthEvent)
        .where(HealthEvent.user_id == user_id)
        .order_by(HealthEvent.timestamp.desc())
        .limit(limit_events)
    )
    rows = list(db.scalars(stmt).all())
    rows.reverse()  # chronological for engines

    views = _to_views(rows)
    mode = compute_mode(views)
    risk_codes = detect_risks(views)
    risks_ru = [RISK_LABEL_RU.get(c, c) for c in risk_codes]

    prediction = build_prediction(risk_codes) or predict_consequences(mode, risk_codes)
    effect = system_effect_lines(mode, risk_codes)
    commands = build_commands(mode, risk_codes)

    disclaimer: str | None = None
    if _severe_symptom(rows):
        disclaimer = (
            "При тяжёлых симптомах не откладывайте обращение к врачу или скорой помощи. "
            "Это не диагноз и не замена очной консультации."
        )

    return AnalysisResponse(
        mode=mode,
        mode_ru=MODE_LABEL_RU.get(mode, mode.value),
        risks=risks_ru,
        system_effect=effect,
        prediction=prediction,
        commands=commands,
        disclaimer=disclaimer,
    )
