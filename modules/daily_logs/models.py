import uuid

from sqlalchemy import CheckConstraint, Column, Date, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from db.database import Base


class DailyLog(Base):
    """
    Maps to tracker.daily_logs.

    One row per (user_id, date) — enforced by the DB unique constraint.
    Tracks a daily summary: calories consumed, workouts completed, recovery notes.

    Constraints (mirrors DB CHECK constraints):
      - calories_consumed >= 0
      - workouts_completed >= 0
    """
    __tablename__ = "daily_logs"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="daily_logs_user_id_date_key"),
        CheckConstraint("calories_consumed >= 0", name="daily_logs_calories_consumed_check"),
        CheckConstraint("workouts_completed >= 0", name="daily_logs_workouts_completed_check"),
        {"schema": "tracker"},
    )

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id             = Column(UUID(as_uuid=True), nullable=False)
    date                = Column(Date, nullable=False)
    calories_consumed   = Column(Integer, nullable=True)
    workouts_completed  = Column(Integer, nullable=True)
    recovery_notes      = Column(Text, nullable=True)
