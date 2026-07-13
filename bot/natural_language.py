"""Conservative Russian free-text parser for HealthOS journal events.

The parser intentionally accepts only explicit, high-confidence phrases.  It is
not a medical interpreter: ambiguous text is returned to the user for
clarification instead of being written to the journal.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


NUMBER = r"(\d+(?:[.,]\d+)?)"


@dataclass(frozen=True)
class ParsedEvent:
    payload: dict[str, Any]
    acknowledgement: str


def _number(value: str) -> float:
    return float(value.replace(",", "."))


def _volume_ml(value: str, unit: str | None) -> float:
    amount = _number(value)
    if unit and unit.lower() in {"л", "литр", "литра", "литров"}:
        return amount * 1000
    return amount


def parse_event(text: str) -> ParsedEvent | None:
    """Parse one explicit journal event from a Russian message."""

    original = " ".join(text.strip().split())
    low = original.lower().replace("ё", "е")
    if not low or low.startswith("/"):
        return None

    pressure = re.search(
        rf"(?:давлени[ея]|ад)\s*[:=-]?\s*(\d{{2,3}})\s*[/\\]\s*(\d{{2,3}})"
        rf"(?:\s*[,;]?\s*(?:пульс|чсс)\s*[:=-]?\s*(\d{{2,3}}))?",
        low,
    )
    if pressure:
        systolic, diastolic = int(pressure.group(1)), int(pressure.group(2))
        pulse = int(pressure.group(3)) if pressure.group(3) else None
        if not (50 <= systolic <= 260 and 30 <= diastolic <= 180):
            return None
        if pulse is not None and not 25 <= pulse <= 240:
            return None
        metadata: dict[str, Any] = {"systolic": systolic, "diastolic": diastolic}
        if pulse is not None:
            metadata["pulse"] = pulse
        pulse_text = f", пульс {pulse}" if pulse is not None else ""
        return ParsedEvent(
            payload={
                "event_type": "blood_pressure",
                "value": float(systolic),
                "unit": "mmHg",
                "note": original,
                "metadata": metadata,
            },
            acknowledgement=f"Давление {systolic}/{diastolic}{pulse_text}",
        )

    scalar_patterns = (
        ("glucose", r"(?:глюкоз[аы]|сахар)(?:\s+в\s+крови)?", "mmol/L", "Глюкоза"),
        ("uric_acid", r"(?:мочевая\s+кислота|мк)", "µmol/L", "Мочевая кислота"),
    )
    for event_type, marker, unit, label in scalar_patterns:
        match = re.search(rf"{marker}\s*[:=-]?\s*{NUMBER}", low)
        if match:
            value = _number(match.group(1))
            return ParsedEvent(
                payload={"event_type": event_type, "value": value, "unit": unit},
                acknowledgement=f"{label}: {value:g} {unit}",
            )

    water = re.search(
        rf"(?:вод[аыуе]|выпил(?:а)?\s+вод[ы]?|попил(?:а)?)\s*[:=-]?\s*{NUMBER}"
        rf"\s*(мл|л|литр(?:а|ов)?)?",
        low,
    ) or re.search(
        rf"{NUMBER}\s*(мл|л|литр(?:а|ов)?)\s+(?:вод[аыуе]|водички)", low
    )
    if water:
        value = _volume_ml(water.group(1), water.group(2))
        return ParsedEvent(
            payload={"event_type": "water", "value": value, "unit": "ml"},
            acknowledgement=f"Вода: {value:g} мл",
        )

    for event_type, marker, label in (
        ("coffee", r"кофе", "Кофе"),
        ("tea", r"(?:чай|чая)", "Чай"),
    ):
        if re.search(marker, low):
            volume = re.search(rf"{NUMBER}\s*(мл|л|литр(?:а|ов)?)", low)
            if volume:
                value = _volume_ml(volume.group(1), volume.group(2))
                return ParsedEvent(
                    payload={"event_type": event_type, "value": value, "unit": "ml"},
                    acknowledgement=f"{label}: {value:g} мл",
                )
            return None

    sauna = re.search(rf"(?:сауна|баня)\D{{0,16}}{NUMBER}\s*(?:мин|минут)", low)
    if sauna:
        minutes = _number(sauna.group(1))
        return ParsedEvent(
            payload={"event_type": "sauna", "value": minutes, "unit": "min"},
            acknowledgement=f"Сауна: {minutes:g} мин",
        )

    if re.search(r"\b(?:тренировк\w*|тренил\w*|занимал(?:ся|ась)|пробежк\w*)\b", low):
        return ParsedEvent(
            payload={"event_type": "workout", "note": original},
            acknowledgement="Тренировка записана",
        )

    if re.search(r"\b(?:принял(?:а)?|выпил(?:а)?)\b", low):
        if re.search(r"\b(?:витамин\w*|магний|омега|бад\w*|добавк\w*)\b", low):
            return ParsedEvent(
                payload={"event_type": "supplement", "note": original},
                acknowledgement="Добавка записана",
            )
        if re.search(r"\b(?:таблетк\w*|лекарств\w*|препарат\w*)\b", low):
            return ParsedEvent(
                payload={"event_type": "medication", "note": original},
                acknowledgement="Приём лекарства записан",
            )

    if re.search(r"\b(?:съел(?:а)?|поел(?:а)?|завтрак\w*|обед\w*|ужин\w*|перекус\w*)\b", low):
        return ParsedEvent(
            payload={"event_type": "food", "note": original},
            acknowledgement="Еда записана",
        )

    symptom_markers = (
        r"\bболит\b",
        r"\bтошнит\b",
        r"\bодышк\w*\b",
        r"\bголовокруж\w*\b",
        r"\bтемператур\w*\b",
        r"\bсимптом\w*\b",
        r"\bболь\b",
        r"\bобморок\w*\b",
    )
    if any(re.search(marker, low) for marker in symptom_markers):
        return ParsedEvent(
            payload={"event_type": "symptom", "note": original},
            acknowledgement="Самочувствие записано",
        )

    return None
