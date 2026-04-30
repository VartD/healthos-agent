import enum
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class EventType(str, enum.Enum):
    water = "water"
    glucose = "glucose"
    uric_acid = "uric_acid"
    blood_pressure = "blood_pressure"
    food = "food"
    coffee = "coffee"
    tea = "tea"
    supplement = "supplement"
    medication = "medication"
    workout = "workout"
    sauna = "sauna"
    sleep = "sleep"
    symptom = "symptom"


class HealthEvent(Base):
    __tablename__ = "health_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType), nullable=False)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
