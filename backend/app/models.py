import enum
from datetime import date, datetime, time, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
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


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = (
        CheckConstraint(
            "sleep_goal_minutes >= 180 AND sleep_goal_minutes <= 720",
            name="ck_user_profiles_sleep_goal",
        ),
    )

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Yekaterinburg")
    sleep_goal_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=480)
    morning_reminder: Mapped[time | None] = mapped_column(Time(), nullable=True)
    evening_reminder: Mapped[time | None] = mapped_column(Time(), nullable=True)
    reminders_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class SleepCheckin(Base):
    __tablename__ = "sleep_checkins"
    __table_args__ = (
        UniqueConstraint("user_id", "sleep_date", name="uq_sleep_checkins_user_date"),
        CheckConstraint(
            "duration_minutes > 0 AND duration_minutes <= 1440",
            name="ck_sleep_checkins_duration",
        ),
        CheckConstraint("quality >= 1 AND quality <= 5", name="ck_sleep_checkins_quality"),
        CheckConstraint(
            "awakenings >= 0 AND awakenings <= 20",
            name="ck_sleep_checkins_awakenings",
        ),
        CheckConstraint("energy >= 1 AND energy <= 5", name="ck_sleep_checkins_energy"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("user_profiles.user_id", ondelete="CASCADE"), index=True
    )
    health_event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("health_events.id", ondelete="CASCADE"), unique=True
    )
    sleep_date: Mapped[date] = mapped_column(Date(), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    quality: Mapped[int] = mapped_column(Integer, nullable=False)
    awakenings: Mapped[int] = mapped_column(Integer, nullable=False)
    energy: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
