from pydantic import BaseModel
from typing import Optional


class WorkoutResponseSchema(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    goal: str
    duration_minutes: Optional[int] = None
    difficulty: Optional[str] = None

    class Config:
        from_attributes = True