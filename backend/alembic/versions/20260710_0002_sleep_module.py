"""Add user profiles and structured sleep check-ins.

Revision ID: 20260710_0002
Revises: 20260710_0001
Create Date: 2026-07-10
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260710_0002"
down_revision: str | None = "20260710_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("sleep_goal_minutes", sa.Integer(), nullable=False),
        sa.Column("morning_reminder", sa.Time(), nullable=True),
        sa.Column("evening_reminder", sa.Time(), nullable=True),
        sa.Column("reminders_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "sleep_goal_minutes >= 180 AND sleep_goal_minutes <= 720",
            name="ck_user_profiles_sleep_goal",
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "sleep_checkins",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("health_event_id", sa.Integer(), nullable=False),
        sa.Column("sleep_date", sa.Date(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.Column("awakenings", sa.Integer(), nullable=False),
        sa.Column("energy", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["health_event_id"], ["health_events.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user_profiles.user_id"], ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "duration_minutes > 0 AND duration_minutes <= 1440",
            name="ck_sleep_checkins_duration",
        ),
        sa.CheckConstraint(
            "quality >= 1 AND quality <= 5", name="ck_sleep_checkins_quality"
        ),
        sa.CheckConstraint(
            "awakenings >= 0 AND awakenings <= 20",
            name="ck_sleep_checkins_awakenings",
        ),
        sa.CheckConstraint(
            "energy >= 1 AND energy <= 5", name="ck_sleep_checkins_energy"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("health_event_id"),
        sa.UniqueConstraint(
            "user_id", "sleep_date", name="uq_sleep_checkins_user_date"
        ),
    )
    op.create_index(
        op.f("ix_sleep_checkins_user_id"),
        "sleep_checkins",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_sleep_checkins_user_id"), table_name="sleep_checkins")
    op.drop_table("sleep_checkins")
    op.drop_table("user_profiles")
