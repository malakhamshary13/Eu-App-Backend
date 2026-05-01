from sqlalchemy import Column, String, Boolean, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from db.database import Base


class Exercise(Base):
    """
    Maps to library.exercises.
    Stores the master exercise library — both admin-seeded and user-custom entries.
    """
    __tablename__ = "exercises"
    __table_args__ = {'schema': 'library'}

    id                         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id                  = Column(String, unique=True, nullable=True)   # original ID from JSON seed data
    title                      = Column(String, nullable=False)
    exercise_type              = Column(String, nullable=True)                # 'weight_reps' | 'reps_only' | 'duration'
    muscle_group               = Column(String, nullable=True)                # primary muscle group
    equipment_category         = Column(String, nullable=True)                # 'barbell' | 'dumbbell' | 'machine' | 'none'
    url                        = Column(Text, nullable=True)                  # video / resource URL
    media_type                 = Column(String, nullable=True)                # 'video' | 'gif' | 'image'
    thumbnail_url              = Column(Text, nullable=True)
    instructions               = Column(Text, nullable=True)
    manual_tag                 = Column(String, nullable=True)                # search / filter helper tag
    priority                   = Column(Integer, nullable=False, default=0)   # display ordering
    is_custom                  = Column(Boolean, nullable=False, default=False)
    is_archived                = Column(Boolean, nullable=False, default=False)
    hundred_percent_bodyweight = Column(Boolean, nullable=False, default=False)

    # One-to-many: one exercise → many secondary muscles
    secondary_muscles = relationship(
        "ExerciseSecondaryMuscle",
        back_populates="exercise",
        cascade="all, delete-orphan",
        lazy="selectin",          # auto-loaded with the exercise
    )


class ExerciseSecondaryMuscle(Base):
    """
    Maps to library.exercise_secondary_muscles.
    Stores secondary muscle groups for a given exercise.
    """
    __tablename__ = "exercise_secondary_muscles"
    __table_args__ = {'schema': 'library'}

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exercise_id = Column(
        UUID(as_uuid=True),
        ForeignKey("library.exercises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    muscle_name = Column(String, nullable=False)

    exercise = relationship("Exercise", back_populates="secondary_muscles")