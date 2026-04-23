from sqlalchemy import Column, Integer, String, Boolean, DateTime, SmallInteger
from datetime import datetime
from db.database import Base


class Exercise(Base):
    __tablename__ = "Exercises"
    __table_args__ = {'schema': 'library'}

    ExerciseId = Column(Integer, primary_key=True, autoincrement=True)
    ExerciseCode = Column(String(8), unique=True, nullable=False)
    Name = Column(String(200), nullable=False)
    Priority = Column(SmallInteger, nullable=False, default=10)
    TargetMuscle = Column(String(100), nullable=False)
    ExerciseType = Column(String(50), nullable=False)
    EquipmentCategory = Column(String(50), nullable=False)
    MediaUrl = Column(String(500), nullable=True)
    MediaType = Column(String(20), nullable=True, default='video')
    ThumbnailUrl = Column(String(500), nullable=True)
    ManualTag = Column(String(200), nullable=True)
    Instructions = Column(String, nullable=True)       # NVARCHAR(MAX)
    IsCustom = Column(Boolean, nullable=False, default=False)
    IsArchived = Column(Boolean, nullable=False, default=False)
    IsBodyweightOnly = Column(Boolean, nullable=False, default=False)
    WorkoutCategory = Column(String(20), nullable=False, default='Fitness')
    CreatedAt = Column(DateTime, nullable=False, default=datetime.utcnow)
    UpdatedAt = Column(DateTime, nullable=False, default=datetime.utcnow)
