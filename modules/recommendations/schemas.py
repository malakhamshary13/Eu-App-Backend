from pydantic import BaseModel
from typing import Optional
from modules.meals.schemas import MealResponseSchema
from modules.workouts.schemas import WorkoutResponseSchema


class RecommendationResponseSchema(BaseModel):
    meal: Optional[MealResponseSchema] = None
    workout: Optional[WorkoutResponseSchema] = None