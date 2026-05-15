import uuid
from typing import List

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core.auth import get_current_user
from core.limiter import limiter
from db.database import get_db
from modules.rehab.schemas import (
    RehabExerciseOut,
    RehabConditionOut,
    SetRehabConditionRequest,
    UserRehabConditionOut,
    RehabPlanCreate, RehabPlanUpdate,
    RehabPlanListItem, RehabPlanOut,
    RehabRoutineCreate, RehabRoutineUpdate, RehabRoutineOut,
    RehabRoutineExerciseCreate, RehabRoutineExerciseOut,
)
from modules.rehab.service import RehabService

router = APIRouter(prefix="/rehab", tags=["Rehab"])
service = RehabService()


# ══════════════════════════════════════════════════════════════════
# ENDPOINT 1 — GET /rehab/exercises
# Return all rehab exercises scoped to the user's active condition.
# Only users with role='rehab' may call this.
# ══════════════════════════════════════════════════════════════════

@router.get(
    "/exercises",
    response_model=List[RehabExerciseOut],
    summary="Get exercises for my rehab condition",
)
@limiter.limit("30/minute")
def get_my_rehab_exercises(
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the rehab exercise library filtered to the user's **active rehab condition**
    (determined by their active `rehab_plan.condition_id`).

    - If the user has an active plan with a condition → returns exercises mapped to that condition.
    - If no condition is linked → returns the **full** rehab exercise library.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.get_exercises_for_user(db, user_id)


# ══════════════════════════════════════════════════════════════════
# ENDPOINT 2 — PUT /rehab/my-condition
# Set (or clear) the user's rehab condition + injury notes.
# ══════════════════════════════════════════════════════════════════

@router.get(
    "/conditions",
    response_model=List[RehabConditionOut],
    summary="List all available rehab conditions",
)
@limiter.limit("30/minute")
def list_conditions(
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the full list of rehab conditions from the library.
    Use the `id` from this response when calling `PUT /rehab/my-condition`.
    """
    return service.list_conditions(db)


@router.put(
    "/my-condition",
    response_model=UserRehabConditionOut,
    summary="Set my rehab condition",
)
@limiter.limit("20/minute")
def set_my_condition(
    request: Request,
    data: SetRehabConditionRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update the authenticated user's rehab condition on their **health profile**.

    | Field | Effect |
    |---|---|
    | `condition_id` | Links to a `library.rehab_conditions` row. Pass `null` to clear. |
    | `injury_details` | Free-text description of the injury. |
    | `recovery_stage` | E.g. `"acute"`, `"sub-acute"`, `"chronic"`. |

    **Prerequisite:** A health profile must exist (`POST /auth/health-profile`).
    """
    user_id = uuid.UUID(str(current_user.id))
    health = service.set_rehab_condition(db, user_id, data)
    return UserRehabConditionOut(
        user_id=health.user_id,
        condition_id=data.condition_id,
        injury_details=health.injury_details,
        recovery_stage=health.recovery_stage,
        updated_at=health.updated_at,
    )


# ══════════════════════════════════════════════════════════════════
# ENDPOINT 3 — Rehab Plan CRUD
# POST / GET / PATCH / DELETE  /rehab/plans
# ══════════════════════════════════════════════════════════════════

@router.get(
    "/plans",
    response_model=List[RehabPlanListItem],
    summary="List my rehab plans",
)
@limiter.limit("30/minute")
def list_my_plans(
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns all rehab plans owned by the authenticated user (newest first)."""
    user_id = uuid.UUID(str(current_user.id))
    return service.list_my_plans(db, user_id)


@router.post(
    "/plans",
    response_model=RehabPlanOut,
    status_code=201,
    summary="Create a rehab plan",
)
@limiter.limit("10/minute")
def create_plan(
    request: Request,
    data: RehabPlanCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new personal rehab plan.

    **Body:**
    - `title` — required
    - `description` — optional
    - `condition_id` — optional UUID from `GET /rehab/conditions`

    Add routines afterwards via `POST /rehab/plans/{plan_id}/routines`.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.create_plan(db, user_id, data)


@router.get(
    "/plans/{plan_id}",
    response_model=RehabPlanOut,
    summary="Get a rehab plan with routines and exercises",
)
@limiter.limit("30/minute")
def get_plan(
    request: Request,
    plan_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the full rehab plan including all routines and their exercises.
    Raises **403** if the authenticated user does not own this plan.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.get_plan(db, plan_id, user_id)


@router.patch(
    "/plans/{plan_id}",
    response_model=RehabPlanOut,
    summary="Update a rehab plan (owner only)",
)
@limiter.limit("20/minute")
def update_plan(
    request: Request,
    plan_id: uuid.UUID,
    data: RehabPlanUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Partially update a rehab plan — only fields that are sent are changed.

    | Field | Notes |
    |---|---|
    | `title` | Rename the plan |
    | `description` | Update description |
    | `condition_id` | Re-link to a different condition (or `null` to unlink) |
    | `is_active` | Toggle active/inactive |
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.update_plan(db, plan_id, user_id, data)


@router.delete(
    "/plans/{plan_id}",
    summary="Delete a rehab plan (owner only)",
)
@limiter.limit("10/minute")
def delete_plan(
    request: Request,
    plan_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permanently delete a rehab plan and all its routines and exercises."""
    user_id = uuid.UUID(str(current_user.id))
    return service.delete_plan(db, plan_id, user_id)


# ──────────────────────────────────────────
# Routine management (within a plan)
# ──────────────────────────────────────────

@router.post(
    "/plans/{plan_id}/routines",
    response_model=RehabRoutineOut,
    status_code=201,
    summary="Add a routine to a plan",
)
@limiter.limit("10/minute")
def create_routine(
    request: Request,
    plan_id: uuid.UUID,
    data: RehabRoutineCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new routine inside a rehab plan.

    **Body:**
    - `name` — e.g. `"Morning Mobility"`, `"Knee Strengthening Day 1"`
    - `order_index` — display order (default 0)

    Add exercises to the routine via `POST /rehab/routines/{routine_id}/exercises`.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.create_routine(db, plan_id, user_id, data)


@router.patch(
    "/routines/{routine_id}",
    response_model=RehabRoutineOut,
    summary="Update a routine (owner only)",
)
@limiter.limit("20/minute")
def update_routine(
    request: Request,
    routine_id: uuid.UUID,
    data: RehabRoutineUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rename a routine or change its order index."""
    user_id = uuid.UUID(str(current_user.id))
    return service.update_routine(db, routine_id, user_id, data)


@router.delete(
    "/routines/{routine_id}",
    summary="Delete a routine and its exercises (owner only)",
)
@limiter.limit("10/minute")
def delete_routine(
    request: Request,
    routine_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a routine slot and all exercises inside it."""
    user_id = uuid.UUID(str(current_user.id))
    return service.delete_routine(db, routine_id, user_id)


# ──────────────────────────────────────────
# Exercise management (within a routine)
# ──────────────────────────────────────────

@router.post(
    "/routines/{routine_id}/exercises",
    response_model=RehabRoutineExerciseOut,
    status_code=201,
    summary="Add an exercise to a routine",
)
@limiter.limit("20/minute")
def add_exercise_to_routine(
    request: Request,
    routine_id: uuid.UUID,
    data: RehabRoutineExerciseCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Append a single exercise to an existing routine.

    **Body:**
    - `exercise_id` — UUID from `GET /rehab/exercises`
    - `sets`, `reps` — optional rep prescription
    - `hold_time_seconds` — for isometric / static holds
    - `rest_seconds` — rest between sets
    - `notes` — physiotherapist notes
    - `order_index` — ordering within the routine (default 0)
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.add_exercise_to_routine(db, routine_id, user_id, data)


@router.delete(
    "/routines/exercises/{entry_id}",
    summary="Remove an exercise from a routine (owner only)",
)
@limiter.limit("20/minute")
def delete_routine_exercise(
    request: Request,
    entry_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a single exercise entry from a routine (does not delete the exercise from the library)."""
    user_id = uuid.UUID(str(current_user.id))
    return service.delete_routine_exercise(db, entry_id, user_id)
