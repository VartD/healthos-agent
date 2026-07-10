"""Create the initial health_events schema.

Revision ID: 20260710_0001
Revises: None
Create Date: 2026-07-10
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260710_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EVENT_TYPES = (
    "water",
    "glucose",
    "uric_acid",
    "blood_pressure",
    "food",
    "coffee",
    "tea",
    "supplement",
    "medication",
    "workout",
    "sauna",
    "sleep",
    "symptom",
)


def upgrade() -> None:
    op.create_table(
        "health_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.Enum(*EVENT_TYPES, name="eventtype"), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_health_events_user_id"),
        "health_events",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_health_events_user_id"), table_name="health_events")
    op.drop_table("health_events")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(*EVENT_TYPES, name="eventtype").drop(bind, checkfirst=True)
