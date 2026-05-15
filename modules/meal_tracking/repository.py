import uuid
from datetime import date
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from modules.meal_tracking.models import UserMealSchedule
from modules.meal_tracking.schemas import (
    MealScheduleCreate,
    MealScheduleEatenUpdate,
    MealScheduleListResponse,
    MealScheduleResponse,
)
from modules.meals.models import Meal


class MealTrackingRepository:

    def _get_schedule_or_404(
        self,
        db: Session,
        schedule_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> UserMealSchedule:
        schedule = (
            db.query(UserMealSchedule)
            .filter(
                UserMealSchedule.id == schedule_id,
                UserMealSchedule.user_id == user_id,
            )
            .first()
        )
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meal schedule item not found.",
            )
        return schedule

    def create_schedule(
        self,
        db: Session,
        user_id: uuid.UUID,
        data: MealScheduleCreate,
    ) -> MealScheduleResponse:
        meal_exists = db.query(Meal.id).filter(Meal.id == data.meal_id).first()
        if not meal_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Meal {data.meal_id} not found.",
            )

        schedule = UserMealSchedule(
            user_id=user_id,
            meal_id=data.meal_id,
            scheduled_date=data.scheduled_date,
            meal_type=data.meal_type,
            is_eaten=data.is_eaten,
            eaten_date=data.eaten_date,
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return MealScheduleResponse.from_orm_schedule(schedule)

    def update_eaten_status(
        self,
        db: Session,
        schedule_id: uuid.UUID,
        user_id: uuid.UUID,
        data: MealScheduleEatenUpdate,
    ) -> MealScheduleResponse:
        schedule = self._get_schedule_or_404(db, schedule_id, user_id)
        schedule.is_eaten = data.is_eaten
        schedule.eaten_date = data.eaten_date
        db.commit()
        db.refresh(schedule)
        return MealScheduleResponse.from_orm_schedule(schedule)

    def get_eaten_meals(
        self,
        db: Session,
        user_id: uuid.UUID,
        scheduled_date: Optional[date] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        meal_type: Optional[str] = None,
    ) -> MealScheduleListResponse:
        q = db.query(UserMealSchedule).filter(
            UserMealSchedule.user_id == user_id,
            UserMealSchedule.is_eaten.is_(True),
        )

        if scheduled_date:
            q = q.filter(UserMealSchedule.scheduled_date == scheduled_date)
        if from_date:
            q = q.filter(UserMealSchedule.scheduled_date >= from_date)
        if to_date:
            q = q.filter(UserMealSchedule.scheduled_date <= to_date)
        if meal_type:
            q = q.filter(UserMealSchedule.meal_type == meal_type)

        schedules = (
            q.order_by(UserMealSchedule.scheduled_date.desc())
            .all()
        )
        return MealScheduleListResponse(
            total=len(schedules),
            results=[MealScheduleResponse.from_orm_schedule(s) for s in schedules],
        )
