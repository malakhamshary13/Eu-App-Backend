import uuid

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey,
    Integer, Numeric, String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from db.database import Base


class WorkoutSession(Base):
    """
    Maps to tracker.workout_sessions.

    Lifecycle (status):
      scheduled → in_progress → completed
                              → abandoned
      scheduled → skipped

    A session always belongs to one user (user_id).
    Optionally references a workout plan (workout_plan_id) and the
    specific routine (routine_id) that was executed that day so that
    pre-planned sets can be compared to actual performance.
    """
    __tablename__ = "workout_sessions"
    __table_args__ = {"schema": "tracker"}

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True), nullable=False)
    workout_plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("plans.workout_plans.id", ondelete="SET NULL"),
        nullable=True,
    )
    routine_id      = Column(
        UUID(as_uuid=True),
        ForeignKey("plans.workout_plan_routines.id", ondelete="SET NULL"),
        nullable=True,
    )
    scheduled_date  = Column(Date, nullable=True)
    started_at      = Column(DateTime(timezone=True), nullable=True)
    completed_at    = Column(DateTime(timezone=True), nullable=True)
    status          = Column(String, nullable=False, default="scheduled")
    # 'scheduled' | 'in_progress' | 'completed' | 'abandoned' | 'skipped'

    # All logged sets for this session
    items = relationship(
        "WorkoutSessionItem",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="(WorkoutSessionItem.exercise_id, WorkoutSessionItem.set_number)",
    )


class WorkoutSessionItem(Base):
    """
    Maps to tracker.workout_session_items.

    Each row represents ONE SET of ONE EXERCISE within a session.

    Constraints (enforced by DB + application):
      - set_number  > 0
      - reps_completed >= 0
      - weight_used    >= 0.0
      - is_completed   defaults to False (set True when the user finishes the set)
    """
    __tablename__ = "workout_session_items"
    __table_args__ = {"schema": "tracker"}

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id      = Column(
        UUID(as_uuid=True),
        ForeignKey("tracker.workout_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    exercise_id     = Column(
        UUID(as_uuid=True),
        ForeignKey("library.exercises.id", ondelete="RESTRICT"),
        nullable=False,
    )
    set_number      = Column(Integer, nullable=False)   # 1-based
    reps_completed  = Column(Integer, nullable=True)
    weight_used     = Column(Numeric(6, 2), nullable=True)
    is_completed    = Column(Boolean, nullable=False, default=False)

    session  = relationship("WorkoutSession", back_populates="items")
    exercise = relationship("Exercise", lazy="selectin", foreign_keys=[exercise_id])
