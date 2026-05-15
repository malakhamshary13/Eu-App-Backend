from sqlalchemy import Column, String, Boolean, Integer, Text, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from sqlalchemy import DateTime

from db.database import Base


class RehabCondition(Base):
    """
    Maps to library.rehab_conditions.
    A clinical rehab condition (e.g. "Lower Back Pain", "Knee Recovery").
    """
    __tablename__ = "rehab_conditions"
    __table_args__ = {'schema': 'library'}

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug        = Column(String, nullable=False, unique=True)
    name        = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    image_url   = Column(Text, nullable=True)
    created_at  = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Exercises linked to this condition via the mapping table
    exercise_mappings = relationship(
        "RehabConditionMapping",
        back_populates="condition",
        lazy="selectin",
    )


class RehabExercise(Base):
    """
    Maps to library.rehab_exercises.
    A therapeutic exercise in the rehab library.
    """
    __tablename__ = "rehab_exercises"
    __table_args__ = {'schema': 'library'}

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug             = Column(String, nullable=False, unique=True)
    title            = Column(Text, nullable=False)
    media_type       = Column(Text, nullable=True, default='youtube')
    youtube_id       = Column(Text, nullable=True)
    youtube_url      = Column(Text, nullable=True)
    thumbnail_url    = Column(Text, nullable=True)
    image_url        = Column(Text, nullable=True)
    description      = Column(Text, nullable=True)
    muscles_involved = Column(ARRAY(Text), nullable=True, default=list)
    categories       = Column(ARRAY(Text), nullable=True, default=list)
    tags             = Column(ARRAY(Text), nullable=True, default=list)
    created_at       = Column(DateTime(timezone=True), default=datetime.utcnow)


class RehabConditionMapping(Base):
    """
    Maps to library.rehab_condition_mapping.
    Many-to-many join between rehab conditions and rehab exercises.
    """
    __tablename__ = "rehab_condition_mapping"
    __table_args__ = {'schema': 'library'}

    condition_id = Column(
        UUID(as_uuid=True),
        ForeignKey("library.rehab_conditions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    exercise_id = Column(
        UUID(as_uuid=True),
        ForeignKey("library.rehab_exercises.id", ondelete="CASCADE"),
        primary_key=True,
    )

    condition = relationship("RehabCondition", back_populates="exercise_mappings")
    exercise  = relationship("RehabExercise", lazy="selectin")


class RehabPlan(Base):
    """
    Maps to plans.rehab_plans.
    A user's personal rehabilitation plan, optionally tied to a condition.
    """
    __tablename__ = "rehab_plans"
    __table_args__ = {'schema': 'plans'}

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id      = Column(UUID(as_uuid=True), nullable=True)   # FK to auth.users.id
    condition_id = Column(
        UUID(as_uuid=True),
        ForeignKey("library.rehab_conditions.id", ondelete="SET NULL"),
        nullable=True,
    )
    title       = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    is_active   = Column(Boolean, default=True, nullable=True)
    created_at  = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at  = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    condition = relationship("RehabCondition", lazy="selectin")
    routines  = relationship(
        "RehabRoutine",
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="RehabRoutine.order_index",
    )


class RehabRoutine(Base):
    """
    Maps to plans.rehab_routines.
    A single routine (session) inside a rehab plan.
    """
    __tablename__ = "rehab_routines"
    __table_args__ = {'schema': 'plans'}

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id     = Column(
        UUID(as_uuid=True),
        ForeignKey("plans.rehab_plans.id", ondelete="CASCADE"),
        nullable=True,
    )
    name        = Column(Text, nullable=False)
    order_index = Column(Integer, default=0, nullable=False)
    created_at  = Column(DateTime(timezone=True), default=datetime.utcnow)

    plan      = relationship("RehabPlan", back_populates="routines")
    exercises = relationship(
        "RehabRoutineExercise",
        back_populates="routine",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="RehabRoutineExercise.order_index",
    )


class RehabRoutineExercise(Base):
    """
    Maps to plans.rehab_routine_exercises.
    A single exercise slot within a rehab routine, with prescription metadata.
    """
    __tablename__ = "rehab_routine_exercises"
    __table_args__ = {'schema': 'plans'}

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    routine_id        = Column(
        UUID(as_uuid=True),
        ForeignKey("plans.rehab_routines.id", ondelete="CASCADE"),
        nullable=True,
    )
    exercise_id       = Column(
        UUID(as_uuid=True),
        ForeignKey("library.rehab_exercises.id", ondelete="RESTRICT"),
        nullable=True,
    )
    sets              = Column(Integer, nullable=True)
    reps              = Column(Integer, nullable=True)
    hold_time_seconds = Column(Integer, nullable=True)
    rest_seconds      = Column(Integer, nullable=True)
    notes             = Column(Text, nullable=True)
    order_index       = Column(Integer, default=0, nullable=False)
    created_at        = Column(DateTime(timezone=True), default=datetime.utcnow)

    routine  = relationship("RehabRoutine", back_populates="exercises")
    exercise = relationship("RehabExercise", lazy="selectin")
