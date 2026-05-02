from sqlalchemy import Column, String, Boolean, Integer, Text, Date, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from db.database import Base


class WorkoutPlan(Base):
    """
    Maps to plans.workout_plans.
    A workout plan is owned by one user (created_by → auth.users.id).
    Ownership is enforced at the application layer.
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

    # Relationship: one plan → many scheduled routine slots
    plan_routines = relationship(
        "WorkoutPlanRoutine",
        back_populates="workout_plan",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Routine(Base):
    """
    Maps to plans.routines.
    A reusable named group of exercises (e.g. 'Push Day', 'Leg Day').
    """
    __tablename__ = "routines"
    __table_args__ = {'schema': 'plans'}

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name        = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_by  = Column(UUID(as_uuid=True), nullable=True)
    is_template = Column(Boolean, nullable=False, default=False)

    # Relationship: one routine → many exercises
    exercises = relationship(
        "RoutineExercise",
        back_populates="routine",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="RoutineExercise.position",
    )


class RoutineExercise(Base):
    """
    Maps to plans.routine_exercises.
    One row = one exercise entry inside a routine, with sets/reps/weight/rest.
    """
    __tablename__ = "routine_exercises"
    __table_args__ = {'schema': 'plans'}

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    routine_id        = Column(
        UUID(as_uuid=True),
        ForeignKey("plans.routines.id", ondelete="CASCADE"),
        nullable=False,
    )
    exercise_id       = Column(
        UUID(as_uuid=True),
        ForeignKey("library.exercises.id", ondelete="RESTRICT"),
        nullable=False,
    )
    position          = Column(Integer, nullable=False, default=0)   # order within routine
    sets              = Column(Integer, nullable=True)
    reps              = Column(Integer, nullable=True)
    weight_kg         = Column(Numeric(6, 2), nullable=True)
    rest_time_seconds = Column(Integer, nullable=True)

    routine  = relationship("Routine", back_populates="exercises")


class WorkoutPlanRoutine(Base):
    """
    Maps to plans.workout_plan_routines.
    Links a routine into a plan and defines its schedule slot.

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
    routine_id  = Column(
        UUID(as_uuid=True),
        ForeignKey("plans.routines.id", ondelete="RESTRICT"),
        nullable=True,   # NULL when is_rest_day = True
    )
    day_number  = Column(Integer, nullable=True)   # for 'nday' schedule
    day_of_week = Column(Integer, nullable=True)   # for 'weekly' schedule (0=Sun … 6=Sat)
    is_rest_day = Column(Boolean, nullable=False, default=False)
    position    = Column(Integer, nullable=False, default=0)

    workout_plan = relationship("WorkoutPlan", back_populates="plan_routines")
    routine      = relationship("Routine", lazy="selectin")