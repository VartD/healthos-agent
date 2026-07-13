from datetime import datetime
from enum import Enum
import math
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models import EventType


class EventCreate(BaseModel):
    model_config = {"populate_by_name": True}

    user_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9:_-]+$")
    timestamp: datetime | None = None
    event_type: EventType
    value: float | None = None
    unit: str | None = Field(default=None, max_length=64)
    note: str | None = Field(default=None, max_length=4000)
    metadata: dict[str, Any] | None = Field(default=None, alias="metadata")

    @field_validator("user_id", "unit", "note")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def validate_event_payload(self) -> "EventCreate":
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError("value must be a finite number")

        allowed_units: dict[EventType, set[str]] = {
            EventType.water: {"ml", "l", "л", "литр"},
            EventType.glucose: {"mmol/l", "ммоль/л"},
            EventType.uric_acid: {"µmol/l", "umol/l", "мкмоль/л"},
            EventType.blood_pressure: {"mmhg", "мм рт. ст."},
            EventType.coffee: {"ml", "l", "л", "литр"},
            EventType.tea: {"ml", "l", "л", "литр"},
            EventType.sauna: {"min", "мин"},
            EventType.sleep: {"h", "hour", "hours", "ч"},
        }
        if self.event_type in allowed_units:
            normalized_unit = self.unit.lower() if self.unit else None
            if normalized_unit not in allowed_units[self.event_type]:
                allowed = ", ".join(sorted(allowed_units[self.event_type]))
                raise ValueError(
                    f"unit for {self.event_type.value} must be one of: {allowed}"
                )

        bounds: dict[EventType, tuple[float, float]] = {
            EventType.water: (0.0, 10_000.0),
            EventType.glucose: (0.5, 40.0),
            EventType.uric_acid: (10.0, 2_000.0),
            EventType.blood_pressure: (20.0, 300.0),
            EventType.coffee: (0.0, 3_000.0),
            EventType.tea: (0.0, 5_000.0),
            EventType.sauna: (0.0, 300.0),
            EventType.sleep: (0.0, 24.0),
        }
        if self.event_type in bounds:
            if self.value is None:
                raise ValueError(f"value is required for {self.event_type.value}")
            lower, upper = bounds[self.event_type]
            if self.unit and self.unit.lower() in {"l", "л", "литр"}:
                upper /= 1000
            if not lower < self.value <= upper:
                raise ValueError(
                    f"value for {self.event_type.value} must be greater than "
                    f"{lower:g} and no more than {upper:g}"
                )

        if self.event_type in {EventType.food, EventType.symptom} and not self.note:
            raise ValueError(f"note is required for {self.event_type.value}")
        return self


class EventRead(BaseModel):
    id: int
    user_id: str
    timestamp: datetime
    event_type: EventType
    value: float | None
    unit: str | None
    note: str | None
    metadata: dict[str, Any] | None = Field(
        validation_alias="event_metadata",
        serialization_alias="metadata",
    )

    model_config = {"from_attributes": True, "populate_by_name": True}


class Mode(str, Enum):
    STABILIZATION = "STABILIZATION"
    TRAINING = "TRAINING"
    RECOVERY = "RECOVERY"
    DRY_MODE = "DRY_MODE"
    NORMAL = "NORMAL"


class AnalysisResponse(BaseModel):
    mode: Mode
    mode_ru: str
    risks: list[str]
    system_effect: list[str]
    prediction: dict[str, str]
    commands: list[str]
    disclaimer: str | None = None
