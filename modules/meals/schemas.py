from pydantic import BaseModel
from typing import Optional


class MealResponseSchema(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    goal: str
    calories: Optional[int] = None
    protein: Optional[int] = None

    class Config:
        from_attributes = True