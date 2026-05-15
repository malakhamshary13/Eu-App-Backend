import uuid
from typing import List

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core.limiter import limiter

from core.auth import get_current_user
from db.database import get_db
from modules.workouts.schemas import (
    WorkoutPlanCreate, WorkoutPlanUpdate,
    WorkoutPlanResponse, WorkoutPlanListItem,
    CreateRoutineInPlan, WorkoutPlanRoutineResponse,
    RoutineExerciseCreate, RoutineExerciseResponse,
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
@limiter.limit("30/minute")  # read
def list_my_plans(
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns all personal workout plans owned by the authenticated user."""
    user_id = uuid.UUID(str(current_user.id))
    return service.get_my_plans(db, user_id)


@router.post(
    "/plans",
    response_model=WorkoutPlanResponse,
    status_code=201,
    summary="Create a workout plan",
)
@limiter.limit("10/minute")  # write mutation
def create_plan(
    request: Request,
    data: WorkoutPlanCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new personal workout plan (metadata only).
    Use `POST /workouts/plans/{plan_id}/routines` to add routines afterwards.

    **schedule_type:**
    - `"nday"` → routines use `day_number` (1, 2, 3 …)
    - `"weekly"` → routines use `day_of_week` (0=Sun … 6=Sat)
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.create_plan(db, user_id, data)


@router.get(
    "/plans/{plan_id}",
    response_model=WorkoutPlanResponse,
    summary="Get a workout plan with all routines and exercises",
)
@limiter.limit("20/minute")  # read
def get_plan(
    request: Request,
    plan_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the full workout plan including all routines and their exercises.
    Raises **403** if the authenticated user does not own this plan.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.get_plan(db, plan_id, user_id)


@router.put(
    "/plans/{plan_id}",
    response_model=WorkoutPlanResponse,
    summary="Update a workout plan (owner only)",
)
@limiter.limit("20/minute")  # write mutation
def update_plan(
    request: Request,
    plan_id: uuid.UUID,
    data: WorkoutPlanUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Partially update plan metadata. Only sent fields are changed."""
    user_id = uuid.UUID(str(current_user.id))
    return service.update_plan(db, plan_id, user_id, data)


@router.delete(
    "/plans/{plan_id}",
    summary="Delete a workout plan (owner only)",
)
@limiter.limit("10/minute")  # write mutation
def delete_plan(
    request: Request,
    plan_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permanently delete a plan and all its routines/exercises."""
    user_id = uuid.UUID(str(current_user.id))
    return service.delete_plan(db, plan_id, user_id)


# ──────────────────────────────────────────
# Routine management (within a plan)
# ──────────────────────────────────────────

@router.post(
    "/plans/{plan_id}/routines",
    response_model=WorkoutPlanRoutineResponse,
    status_code=201,
    summary="Add a routine to a plan (owner only)",
)
@limiter.limit("10/minute")  # write mutation
def create_routine_for_plan(
    request: Request,
    plan_id: uuid.UUID,
    data: CreateRoutineInPlan,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new routine and attach it to the plan as a scheduled slot.

    **Body fields:**
    - `name` — routine name (e.g. "Push Day", "Leg Day")
    - `description` — optional
    - `day_number` — for `nday` plans (1, 2, 3 …)
    - `day_of_week` — for `weekly` plans (0=Sun … 6=Sat)
    - `position` — display order within the same day (default 0)
    - `is_rest_day` — mark as rest day (name ignored)

    Raises **403** if you don't own the plan.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.create_routine_for_plan(db, plan_id, user_id, data)


@router.get(
    "/routines/{routine_id}",
    response_model=WorkoutPlanRoutineResponse,
    summary="Get a routine with its exercises",
)
@limiter.limit("30/minute")  # read
def get_routine(
    request: Request,
    routine_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns a single routine with all its exercises and full exercise details.
    Raises **403** if you don't own the parent plan.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.get_routine(db, routine_id, user_id)


@router.delete(
    "/routines/{routine_id}",
    summary="Delete a routine and its exercises (owner only)",
)
@limiter.limit("30/minute")  # write mutation
def delete_routine(
    request: Request,
    routine_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a routine slot and all its exercises."""
    user_id = uuid.UUID(str(current_user.id))
    return service.delete_routine(db, routine_id, user_id)


# ──────────────────────────────────────────
# Exercise management (within a routine)
# ──────────────────────────────────────────

@router.post(
    "/routines/{routine_id}/exercises",
    response_model=RoutineExerciseResponse,
    status_code=201,
    summary="Add an exercise to a routine (owner only)",
)
@limiter.limit("30/minute")  # write mutation
def add_exercise_to_routine(
    request: Request,
    routine_id: uuid.UUID,
    data: RoutineExerciseCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Append a single exercise to an existing routine.

    **Body fields:**
    - `exercise_id` — UUID from `library.exercises`
    - `position` — ordering within the routine (default 0)
    - `sets`, `reps`, `weight_kg`, `rest_time_seconds` — all optional

    Returns the created entry with full exercise details embedded.
    Raises **403** if you don't own the routine's parent plan.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.add_exercise_to_routine(db, routine_id, user_id, data)