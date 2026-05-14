import uuid
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from modules.meal_tracking.repository import MealTrackingRepository
from modules.meal_tracking.schemas import MealScheduleCreate, MealScheduleEatenUpdate

_repo = MealTrackingRepository()


class MealTrackingService:

    def create_schedule(self, db: Session, user_id: uuid.UUID, data: MealScheduleCreate):
        return _repo.create_schedule(db, user_id, data)

    def update_eaten_status(
        self,
        db: Session,
        schedule_id: uuid.UUID,
        user_id: uuid.UUID,
        data: MealScheduleEatenUpdate,
    ):
        return _repo.update_eaten_status(db, schedule_id, user_id, data)

    def get_eaten_meals(
        self,
        db: Session,
        user_id: uuid.UUID,
        scheduled_date: Optional[date] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        meal_type: Optional[str] = None,
    ):
        return _repo.get_eaten_meals(db, user_id, scheduled_date, from_date, to_date, meal_type)
