from datetime import date, datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator


USER_ID_PATTERN = r"^[A-Za-z0-9:_-]+$"


class ProfileUpsert(BaseModel):
    user_id: str = Field(min_length=1, max_length=128, pattern=USER_ID_PATTERN)
    timezone: str = Field(default="Asia/Yekaterinburg", min_length=1, max_length=64)
    sleep_goal_minutes: int = Field(default=480, ge=180, le=720)
    morning_reminder: time | None = None
    evening_reminder: time | None = None
    reminders_enabled: bool = False

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("unknown IANA timezone") from exc
        return value


class ProfileRead(ProfileUpsert):
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SleepCheckinUpsert(BaseModel):
    user_id: str = Field(min_length=1, max_length=128, pattern=USER_ID_PATTERN)
    sleep_date: date | None = None
    duration_hours: float = Field(gt=0, le=24)
    quality: int = Field(ge=1, le=5)
    awakenings: int = Field(ge=0, le=20)
    energy: int = Field(ge=1, le=5)
    note: str | None = Field(default=None, max_length=2000)


class SleepCheckinRead(BaseModel):
    id: int
    user_id: str
    sleep_date: date
    duration_hours: float
    quality: int
    awakenings: int
    energy: int
    note: str | None
    created_at: datetime
    updated_at: datetime


class SleepWeeklySummary(BaseModel):
    user_id: str
    period_start: date
    period_end: date
    days_logged: int
    average_duration_hours: float | None
    average_quality: float | None
    average_awakenings: float | None
    average_energy: float | None
    goal_met_days: int
    sleep_goal_hours: float
    next_best_action: str
