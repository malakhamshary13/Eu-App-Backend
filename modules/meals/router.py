import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from core.limiter import limiter

from core.auth import get_current_user, require_admin
from db.database import get_db
from modules.meals.schemas import (
    MealCreate, MealDetailResponse, PaginatedMeals, MealFilterOptions,
)
from modules.meals.service import MealService

router = APIRouter(prefix="/meals", tags=["Meals"])
service = MealService()


# ──────────────────────────────────────────
# Public / authenticated
# ──────────────────────────────────────────

@router.get("/filters", response_model=MealFilterOptions, summary="Get available meal filter tags")
@limiter.limit("60/minute")  # read
def get_filter_options(
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns all distinct tag values in the meal library for populating filter UIs."""
    return service.get_filter_options(db)


@router.get("/recommend", response_model=PaginatedMeals, summary="Recommend meals based on my health profile")
@limiter.limit("20/minute")  # expensive DB query — tighter cap
def recommend_meals(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns meals recommended for the authenticated user based on:

    1. **Chronic conditions** (from your health profile) — excludes forbidden ingredients/tags,
       requires necessary labels, and enforces per-serving nutrition thresholds from
       `library.condition_nutrition_rules`.
    2. **Primary goal** (fallback when no conditions are linked) — applies goal-based defaults:
       - `weight_loss` → low calorie (≤450 kcal), high protein (≥15g), low fat (≤18g)
       - `muscle_gain` → high protein (≥25g), sufficient calories (≥350 kcal)
       - `rehab` → low sodium (≤600mg)
       - `maintenance` → full library, no filters
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.recommend_meals(db, user_id, page=page, page_size=page_size)


@router.get("/", response_model=PaginatedMeals, summary="List meals (paginated + filtered)")
@limiter.limit("60/minute")  # read — paginated browse
def list_meals(
    request: Request,
    page:          int            = Query(1,    ge=1,                  description="Page number"),
    page_size:     int            = Query(20,   ge=1, le=100,          description="Results per page (max 100)"),
    search:        Optional[str]  = Query(None,                        description="Search by meal title"),
    tag:           Optional[str]  = Query(None,                        description="Filter by tag (e.g. 'vegan', 'high-protein')"),
    tags:          Optional[List[str]] = Query(None,                    description="Filter by multiple tags. Repeat this query param or send comma-separated values."),
    max_calories:  Optional[int]  = Query(None,                        description="Maximum calories per serving"),
    min_protein_g: Optional[float]= Query(None,                        description="Minimum protein in grams"),
    max_fat_g:     Optional[float]= Query(None,                        description="Maximum total fat in grams"),
    max_sodium_mg: Optional[float]= Query(None,                        description="Maximum sodium in mg"),
    max_sugar_g:   Optional[float]= Query(None,                        description="Maximum sugar in grams"),
    use_profile:   bool           = Query(False,                       description="Auto-filter by your health profile goal"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns a paginated, filterable list of meals.

    **All filters are optional and combinable:**
    - `search` — title search (case-insensitive)
    - `tag` — filter by a specific tag name
    - `max_calories`, `min_protein_g`, `max_fat_g`, `max_sodium_mg`, `max_sugar_g` — nutrition thresholds
    - `use_profile=true` — auto-apply goal-based thresholds from your health profile
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.list_meals(
        db,
        page=page, page_size=page_size,
        search=search, tag=tag, tags=tags,
        max_calories=max_calories, min_protein_g=min_protein_g,
        max_fat_g=max_fat_g, max_sodium_mg=max_sodium_mg, max_sugar_g=max_sugar_g,
        use_profile=use_profile, user_id=user_id,
    )


@router.get("/{meal_id}", response_model=MealDetailResponse, summary="Get full meal details")
@limiter.limit("60/minute")  # read
def get_meal(
    request: Request,
    meal_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns full meal details including nutrition, tags, ingredients, and cooking instructions."""
    return service.get_meal(db, meal_id)


# ──────────────────────────────────────────
# Admin-only
# ──────────────────────────────────────────

@router.post("/", response_model=MealDetailResponse, status_code=201, summary="[Admin] Add a meal to the library")
@limiter.limit("30/minute")  # write mutation
def create_meal(
    request: Request,
    data: MealCreate,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Create a new meal in the library with optional nutrition data, tags, and ingredients.
    Only accessible by admins.
    """
    return service.create_meal(db, data)


@router.delete("/{meal_id}", summary="[Admin] Delete a meal")
@limiter.limit("30/minute")  # write mutation
def delete_meal(
    request: Request,
    meal_id: uuid.UUID,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Permanently delete a meal and all its nutrition, tags, and ingredients."""
    return service.delete_meal(db, meal_id)
