from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.models import EventType


class EventCreate(BaseModel):
    model_config = {"populate_by_name": True}

    user_id: str
    timestamp: datetime | None = None
    event_type: EventType
    value: float | None = None
    unit: str | None = None
    note: str | None = None
    metadata: dict[str, Any] | None = Field(default=None, alias="metadata")


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
