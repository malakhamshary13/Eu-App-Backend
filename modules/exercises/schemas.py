from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from db.database import ORMBaseModel


class ExerciseOut(ORMBaseModel):
    """Full exercise response schema – mirrors every column in library.Exercises."""
    ExerciseId: int
    ExerciseCode: str
    Name: str
    Priority: int
    TargetMuscle: str
    ExerciseType: str
    EquipmentCategory: str
    MediaUrl: Optional[str] = None
    MediaType: Optional[str] = None
    ThumbnailUrl: Optional[str] = None
    ManualTag: Optional[str] = None
    Instructions: Optional[str] = None
    IsCustom: bool
    IsArchived: bool
    IsBodyweightOnly: bool
    WorkoutCategory: str
    CreatedAt: datetime
    UpdatedAt: datetime


class ExerciseListRequest(BaseModel):
    """Query params for the GET exercises endpoint."""
    count: int = Field(..., gt=0, le=500, description="Number of exercises to return")
