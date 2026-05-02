import uuid
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.auth import get_current_user
from db.database import get_db
from modules.workouts.schemas import (
    WorkoutPlanCreate, WorkoutPlanUpdate,
    WorkoutPlanResponse, WorkoutPlanListItem,
    PlanRoutineSlotCreate, PlanRoutineSlotResponse,
)
from modules.workouts.service import WorkoutService

router = APIRouter(prefix="/workouts", tags=["Workouts"])
service = WorkoutService()


# ──────────────────────────────────────────
# Workout Plan CRUD
# ──────────────────────────────────────────

@router.get(
    "/plans",
    response_model=List[WorkoutPlanListItem],
    summary="List my workout plans",
)
def list_my_plans(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns all personal workout plans owned by the authenticated user.
    Templates are excluded — those are system-level plans.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.get_my_plans(db, user_id)


@router.post(
    "/plans",
    response_model=WorkoutPlanResponse,
    status_code=201,
    summary="Create a workout plan",
)
def create_plan(
    data: WorkoutPlanCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new personal workout plan.

    You can define routine slots inline in `slots[]`. Each slot can:
    - Provide a full `routine` object to create a new routine
    - Reference an existing routine via `routine_id`
    - Be a rest day with `is_rest_day: true`

    **Schedule modes:**
    - `schedule_type: "nday"` → slots use `day_number` (1, 2, 3 …)
    - `schedule_type: "weekly"` → slots use `day_of_week` (0=Sun … 6=Sat)
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.create_plan(db, user_id, data)


@router.get(
    "/plans/{plan_id}",
    response_model=WorkoutPlanResponse,
    summary="Get a workout plan (owner only)",
)
def get_plan(
    plan_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the full workout plan including all routine slots and exercises.
    Raises **403** if the authenticated user does not own this plan.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.get_plan(db, plan_id, user_id)


@router.put(
    "/plans/{plan_id}",
    response_model=WorkoutPlanResponse,
    summary="Update a workout plan (owner only)",
)
def update_plan(
    plan_id: uuid.UUID,
    data: WorkoutPlanUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Partially update plan metadata (title, dates, difficulty, description, etc.).
    Only fields you include in the body will be changed.
    Raises **403** if the authenticated user does not own this plan.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.update_plan(db, plan_id, user_id, data)


@router.delete(
    "/plans/{plan_id}",
    summary="Delete a workout plan (owner only)",
)
def delete_plan(
    plan_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Permanently delete a workout plan and all its routine slots.
    Raises **403** if the authenticated user does not own this plan.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.delete_plan(db, plan_id, user_id)


# ──────────────────────────────────────────
# Routine slot management (within a plan)
# ──────────────────────────────────────────

@router.post(
    "/plans/{plan_id}/slots",
    response_model=PlanRoutineSlotResponse,
    status_code=201,
    summary="Add a routine slot to a plan (owner only)",
)
def add_routine_slot(
    plan_id: uuid.UUID,
    slot: PlanRoutineSlotCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add a new routine slot to an existing plan.
    Can create the routine inline or reference an existing `routine_id`.
    Raises **403** if the authenticated user does not own this plan.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.add_routine_slot(db, plan_id, user_id, slot)


@router.delete(
    "/plans/{plan_id}/slots/{slot_id}",
    summary="Remove a routine slot from a plan (owner only)",
)
def remove_routine_slot(
    plan_id: uuid.UUID,
    slot_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove a specific routine slot from a plan.
    Raises **403** if the authenticated user does not own this plan.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.remove_routine_slot(db, plan_id, slot_id, user_id)