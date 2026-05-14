import uuid
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field

from db.database import ORMBaseModel


class DailyLogUpsert(BaseModel):
    """
    Create or update the log for a specific date.
    Only provided (non-null) fields are changed on update.
    All numeric fields must be >= 0.
    """
    date:               date
    calories_consumed:  Optional[int]  = Field(None, ge=0, description="Total kcal consumed on this day.")
    workouts_completed: Optional[int]  = Field(None, ge=0, description="Number of workout sessions completed.")
    recovery_notes:     Optional[str]  = Field(None, description="Free-text recovery / wellbeing notes.")


class DailyLogUpdate(BaseModel):
    """PATCH — only the fields you send are changed."""
    calories_consumed:  Optional[int]  = Field(None, ge=0)
    workouts_completed: Optional[int]  = Field(None, ge=0)
    recovery_notes:     Optional[str]  = None


class DailyLogResponse(ORMBaseModel):
    id:                 uuid.UUID
    user_id:            uuid.UUID
    date:               date
    calories_consumed:  Optional[int]  = None
    workouts_completed: Optional[int]  = None
    recovery_notes:     Optional[str]  = None


class DailyLogListResponse(BaseModel):
    total:   int
    results: List[DailyLogResponse]
