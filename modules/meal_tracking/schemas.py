import uuid
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from db.database import ORMBaseModel
from modules.meals.schemas import MealListItem


class MealScheduleCreate(BaseModel):
    meal_id: uuid.UUID
    scheduled_date: datetime
    meal_type: str = Field(..., pattern="^(breakfast|lunch|dinner|snack)$")
    is_eaten: bool = False
    eaten_date: Optional[datetime] = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "meal_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "scheduled_date": "2026-05-14T01:17:09.576Z",
                    "meal_type": "lunch",
                    "is_eaten": False,
                    "eaten_date": None,
                }
            ]
        }
    )


class MealScheduleEatenUpdate(BaseModel):
    schedule_id: uuid.UUID
    is_eaten: bool
    eaten_date: Optional[datetime] = None


class MealScheduleResponse(ORMBaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    meal_id: uuid.UUID
    scheduled_date: datetime
    meal_type: str
    is_eaten: bool
    eaten_date: Optional[datetime] = None
    meal: Optional[MealListItem] = None

    @classmethod
    def from_orm_schedule(cls, schedule):
        return cls(
            id=schedule.id,
            user_id=schedule.user_id,
            meal_id=schedule.meal_id,
            scheduled_date=schedule.scheduled_date,
            meal_type=schedule.meal_type,
            is_eaten=schedule.is_eaten,
            eaten_date=schedule.eaten_date,
            meal=MealListItem.from_orm_meal(schedule.meal) if schedule.meal else None,
        )


class MealScheduleListResponse(BaseModel):
    total: int
    results: List[MealScheduleResponse]
