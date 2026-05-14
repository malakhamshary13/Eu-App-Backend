import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from db.database import Base


class RehabSession(Base):
    """
    Maps to tracker.rehab_sessions.

    Lifecycle (status):
      scheduled → in_progress → completed
                              → skipped

    Each session is scoped to a specific rehab routine from a rehab plan.
    Pain level (1–10) can be recorded at the session level and per exercise.
    """
    __tablename__ = "rehab_sessions"
    __table_args__ = {"schema": "tracker"}

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id        = Column(UUID(as_uuid=True), nullable=False)
    plan_id        = Column(
        UUID(as_uuid=True),
        ForeignKey("plans.rehab_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    routine_id     = Column(
        UUID(as_uuid=True),
        ForeignKey("plans.rehab_routines.id", ondelete="CASCADE"),
        nullable=False,
    )
    scheduled_date = Column(Date, nullable=False)
    status         = Column(String, nullable=False, default="scheduled")
    # 'scheduled' | 'in_progress' | 'completed' | 'skipped'
    started_at     = Column(DateTime(timezone=True), nullable=True)
    completed_at   = Column(DateTime(timezone=True), nullable=True)
    pain_level     = Column(SmallInteger, nullable=True)   # 1–10
    notes          = Column(Text, nullable=True)
    created_at     = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    exercises = relationship(
        "RehabSessionExercise",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="RehabSessionExercise.id",
    )


class RehabSessionExercise(Base):
    """
    Maps to tracker.rehab_session_exercises.

    One row per exercise per rehab session.
    Stores the actual performance vs. the planned prescription:
      - sets_completed, reps_completed, hold_time_seconds
      - is_completed — toggled true when the user finishes this exercise
      - pain_level (1–10) — exercise-level pain rating
    """
    __tablename__ = "rehab_session_exercises"
    __table_args__ = {"schema": "tracker"}

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id          = Column(
        UUID(as_uuid=True),
        ForeignKey("tracker.rehab_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    routine_exercise_id = Column(
        UUID(as_uuid=True),
        ForeignKey("plans.rehab_routine_exercises.id", ondelete="CASCADE"),
        nullable=False,
    )
    exercise_id         = Column(
        UUID(as_uuid=True),
        ForeignKey("library.rehab_exercises.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sets_completed      = Column(SmallInteger, nullable=True)
    reps_completed      = Column(SmallInteger, nullable=True)
    hold_time_seconds   = Column(Integer, nullable=True)
    is_completed        = Column(Boolean, nullable=False, default=False)
    pain_level          = Column(SmallInteger, nullable=True)   # 1–10
    notes               = Column(Text, nullable=True)

    session  = relationship("RehabSession", back_populates="exercises")
    exercise = relationship("RehabExercise", lazy="selectin", foreign_keys=[exercise_id])
