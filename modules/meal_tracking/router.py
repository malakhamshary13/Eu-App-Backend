import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from core.auth import get_current_user
from db.database import get_db
from modules.meal_tracking.schemas import (
    MealScheduleCreate,
    MealScheduleEatenUpdate,
    MealScheduleListResponse,
    MealScheduleResponse,
)
from modules.meal_tracking.service import MealTrackingService

router = APIRouter(prefix="/meal/schedule", tags=["Meal Schedule"])
service = MealTrackingService()


@router.post(
    "/",
    response_model=MealScheduleResponse,
    status_code=201,
    summary="Schedule a meal for a day",
)
def create_meal_schedule(
    data: MealScheduleCreate = Body(
        ...,
        openapi_examples={
            "default": {
                "summary": "Schedule meal",
                "value": {
                    "meal_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "scheduled_date": "2026-05-14T01:17:09.576Z",
                    "meal_type": "lunch",
                    "is_eaten": False,
                    "eaten_date": None,
                },
            }
        },
    ),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add a meal to the authenticated user's daily schedule.
    Use `is_eaten=true` when creating a meal that was already eaten.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.create_schedule(db, user_id, data)


@router.patch(
    "/eaten",
    response_model=MealScheduleResponse,
    summary="Mark a scheduled meal as eaten and add its eaten_date",
)
def update_meal_eaten_status(
    data: MealScheduleEatenUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set `is_eaten=true` when the user eats the meal, or `false` to uncheck it."""
    user_id = uuid.UUID(str(current_user.id))
    return service.update_eaten_status(db, data.schedule_id, user_id, data)


@router.get(
    "/eaten",
    response_model=MealScheduleListResponse,
    summary="Get eaten scheduled meals",
)
def get_eaten_meals(
    date_filter: Optional[date] = Query(None, alias="date", description="Only meals eaten on this scheduled date"),
    from_date: Optional[date] = Query(None, description="Start scheduled date"),
    to_date: Optional[date] = Query(None, description="End scheduled date"),
    meal_type: Optional[str] = Query(None, pattern="^(breakfast|lunch|dinner|snack)$"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the authenticated user's schedule items where `is_eaten=true`."""
    user_id = uuid.UUID(str(current_user.id))
    return service.get_eaten_meals(db, user_id, date_filter, from_date, to_date, meal_type)
