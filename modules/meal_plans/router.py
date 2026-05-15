import uuid
from typing import List

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core.limiter import limiter

from core.auth import get_current_user, require_admin
from db.database import get_db
from modules.meal_plans.schemas import (
    MealPlanCreate, MealPlanUpdate,
    MealPlanResponse, MealPlanListItem,
    MealPlanSlotCreate, MealPlanSlotResponse,
)
from modules.meal_plans.service import MealPlanService

router = APIRouter(prefix="/meal/plans", tags=["Meal Plans"])
service = MealPlanService()


# ──────────────────────────────────────────
# Templates (readable by all authenticated users)
# ──────────────────────────────────────────

@router.get(
    "/templates",
    response_model=List[MealPlanListItem],
    summary="Browse admin meal plan templates",
)
@limiter.limit("60/minute")  # read
def list_templates(
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns all admin-published meal plan templates.
    Templates are visible to all authenticated users and may be optionally
    targeted at a specific medical condition (`target_condition_id`).
    """
    return service.get_templates(db)


# ──────────────────────────────────────────
# Personal plans
# ──────────────────────────────────────────

@router.get(
    "/",
    response_model=List[MealPlanListItem],
    summary="List my meal plans",
)
@limiter.limit("60/minute")  # read
def list_my_plans(
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns all personal (non-template) meal plans owned by the authenticated user."""
    user_id = uuid.UUID(str(current_user.id))
    return service.get_my_plans(db, user_id)


@router.post(
    "/",
    response_model=MealPlanResponse,
    status_code=201,
    summary="Create a meal plan",
)
@limiter.limit("30/minute")  # write mutation
def create_plan(
    request: Request,
    data: MealPlanCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new personal meal plan.

    **Body fields:**
    - `title` — plan name (required)
    - `description` — optional summary
    - `goal_type` — e.g. `weight_loss`, `muscle_gain`, `maintenance`
    - `start_date` / `end_date` — optional date range
    - `target_condition_id` — optional link to a `library.conditions` record
      (e.g. associate this plan with Hypertension or Type 2 Diabetes)

    Once created, add meals via `POST /meal-plans/{id}/slots`.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.create_plan(db, user_id, data)


@router.get(
    "/{plan_id}",
    response_model=MealPlanResponse,
    summary="Get a meal plan with all its meals",
)
@limiter.limit("60/minute")  # read
def get_plan(
    request: Request,
    plan_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the full meal plan with all assigned slot meals (breakfast / lunch / dinner / snack),
    each with embedded compact meal details (title, image, nutrition).

    Accessible if:
    - You own the plan, **or**
    - The plan is a template (`is_template=true`)

    Raises **403** otherwise.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.get_plan(db, plan_id, user_id)


@router.put(
    "/{plan_id}",
    response_model=MealPlanResponse,
    summary="Update a meal plan (owner only)",
)
@limiter.limit("30/minute")  # write mutation
def update_plan(
    request: Request,
    plan_id: uuid.UUID,
    data: MealPlanUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Partially update meal plan metadata.
    Only fields you include in the body will be changed.
    Raises **403** if you don't own this plan.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.update_plan(db, plan_id, user_id, data)


@router.delete(
    "/{plan_id}",
    summary="Delete a meal plan (owner only)",
)
@limiter.limit("30/minute")  # write mutation
def delete_plan(
    request: Request,
    plan_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Permanently delete a meal plan and all its slot assignments.
    Raises **403** if you don't own this plan.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.delete_plan(db, plan_id, user_id)


# ──────────────────────────────────────────
# Slot management
# ──────────────────────────────────────────

@router.post(
    "/{plan_id}/slots",
    response_model=MealPlanSlotResponse,
    status_code=201,
    summary="Assign a meal to a slot in the plan (owner only)",
)
@limiter.limit("30/minute")  # write mutation
def add_slot(
    request: Request,
    plan_id: uuid.UUID,
    data: MealPlanSlotCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Assign a meal to a meal-type slot in the plan.

    **Body fields:**
    - `meal_id` — UUID of a meal from `library.meals`
    - `meal_type` — one of: `breakfast`, `lunch`, `dinner`, `snack`
    - `note` — optional note about why this meal is in this slot

    Returns **409** if this meal is already assigned to the same slot type in this plan.
    Raises **403** if you don't own the plan.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.add_slot(db, plan_id, user_id, data)


@router.delete(
    "/{plan_id}/slots/{slot_id}",
    summary="Remove a meal from a plan slot (owner only)",
)
@limiter.limit("30/minute")  # write mutation
def remove_slot(
    request: Request,
    plan_id: uuid.UUID,
    slot_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove a meal from a specific slot in the plan.
    Raises **403** if you don't own the plan.
    Raises **404** if the slot doesn't exist in this plan.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.remove_slot(db, plan_id, slot_id, user_id)
