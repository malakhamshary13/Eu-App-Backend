from sqlalchemy import Column, String, Boolean, Integer, Text, Date, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from db.database import Base


class WorkoutPlan(Base):
    """
    Maps to plans.workout_plans.
    Owned by one user (created_by → auth.users.id).
    """
    __tablename__ = "workout_plans"
    __table_args__ = {'schema': 'plans'}

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title            = Column(String, nullable=False)
    difficulty_level = Column(String, nullable=True)   # 'beginner' | 'intermediate' | 'advanced'
    schedule_type    = Column(String, nullable=True, default='nday')  # 'nday' | 'weekly'
    description      = Column(Text, nullable=True)
    start_date       = Column(Date, nullable=True)
    end_date         = Column(Date, nullable=True)
    is_template      = Column(Boolean, nullable=False, default=False)
    created_by       = Column(UUID(as_uuid=True), nullable=True)   # FK to auth.users.id
    creator_role     = Column(String, nullable=True, default='user')  # 'admin' | 'user'

    plan_routines = relationship(
        "WorkoutPlanRoutine",
        back_populates="workout_plan",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="WorkoutPlanRoutine.position",
    )


class WorkoutPlanRoutine(Base):
    """
    Maps to plans.workout_plan_routines.
    Each row IS the routine — name & description live here directly.
    No separate plans.routines table.

    Schedule modes (set by parent plan's schedule_type):
      'nday'   → populate day_number (1, 2, 3 …)
      'weekly' → populate day_of_week (0=Sun … 6=Sat)
    """
    __tablename__ = "workout_plan_routines"
    __table_args__ = {'schema': 'plans'}

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workout_plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("plans.workout_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    name        = Column(String, nullable=True)   # NULL when is_rest_day = True
    description = Column(Text, nullable=True)
    day_number  = Column(Integer, nullable=True)   # for 'nday' schedule
    day_of_week = Column(Integer, nullable=True)   # for 'weekly' schedule (0=Sun … 6=Sat)
    is_rest_day = Column(Boolean, nullable=False, default=False)
    position    = Column(Integer, nullable=False, default=0)

    workout_plan = relationship("WorkoutPlan", back_populates="plan_routines")
    exercises    = relationship(
        "RoutineExercise",
        back_populates="routine",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="RoutineExercise.position",
    )


class RoutineExercise(Base):
    """
    Maps to plans.routine_exercises.
    workout_plan_routine_id → plans.workout_plan_routines.id
    """
    __tablename__ = "routine_exercises"
    __table_args__ = {'schema': 'plans'}

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workout_plan_routine_id = Column(
        UUID(as_uuid=True),
        ForeignKey("plans.workout_plan_routines.id", ondelete="CASCADE"),
        nullable=False,
    )
    exercise_id       = Column(
        UUID(as_uuid=True),
        ForeignKey("library.exercises.id", ondelete="RESTRICT"),
        nullable=False,
    )
    position          = Column(Integer, nullable=False, default=0)
    sets              = Column(Integer, nullable=True)
    reps              = Column(Integer, nullable=True)
    weight_kg         = Column(Numeric(6, 2), nullable=True)
    rest_time_seconds = Column(Integer, nullable=True)

    routine  = relationship("WorkoutPlanRoutine", back_populates="exercises")
    exercise = relationship("Exercise", lazy="selectin", foreign_keys=[exercise_id])