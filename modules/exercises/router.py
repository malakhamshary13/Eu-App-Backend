import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from core.limiter import limiter

from core.auth import get_current_user, require_admin
from db.database import get_db
from modules.exercises.schemas import (
    ExerciseCreate, ExerciseUpdate, ExerciseResponse, PaginatedExercises, FilterOptions,
)
from modules.exercises.service import ExerciseService

router = APIRouter(prefix="/exercises", tags=["Exercises"])
service = ExerciseService()


# ──────────────────────────────────────────
# Public / authenticated endpoints
# ──────────────────────────────────────────

@router.get(
    "/filters",
    response_model=FilterOptions,
    summary="Get available filter options",
)
@limiter.limit("60/minute")  # read
def get_filter_options(
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns all distinct non-null values currently present in the exercise library
    for each filterable column (archived exercises excluded).

    Use this to populate filter dropdowns / chips in the UI without hardcoding values.
    """
    return service.get_filter_options(db)


@router.get(
    "/",
    response_model=PaginatedExercises,
    summary="List exercises (paginated + filtered)",
)
@limiter.limit("60/minute")  # read — paginated browse
def get_exercises(
    request: Request,
    # ── Pagination ──
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page (max 100)"),
    # ── Explicit filters ──
    exercise_type: Optional[str] = Query(
        None,
        description="Filter by type: 'weight_reps' | 'reps_only' | 'duration'",
    ),
    muscle_group: Optional[str] = Query(
        None,
        description="Filter by primary muscle group (e.g. 'chest', 'back', 'legs')",
    ),
    equipment_category: Optional[str] = Query(
        None,
        description="Filter by equipment: 'barbell' | 'dumbbell' | 'machine' | 'none'",
    ),
    search: Optional[str] = Query(
        None,
        description="Search exercises by title (case-insensitive)",
    ),
    # ── Boolean filters ──
    hundred_percent_bodyweight: Optional[bool] = Query(
        None,
        description="Filter to bodyweight-only exercises (true) or exclude them (false)",
    ),
    is_custom: Optional[bool] = Query(
        None,
        description="Filter to user-created exercises (true) or library exercises (false)",
    ),
    # ── Profile-based filter ──
    use_profile: bool = Query(
        False,
        description=(
            "If true, auto-filter exercises based on your health profile goal. "
            "Explicit filters still override the profile defaults."
        ),
    ),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns a paginated list of exercises.

    **Filter options (all optional, combinable):**
    - `use_profile=true` — auto-filter based on your health profile's `primary_goal`
    - `exercise_type` — narrow by movement type
    - `muscle_group` — narrow by target muscle
    - `equipment_category` — narrow by required equipment
    - `search` — free-text search on exercise title

    Archived exercises are excluded by default.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.list_exercises(
        db,
        page=page,
        page_size=page_size,
        exercise_type=exercise_type,
        muscle_group=muscle_group,
        equipment_category=equipment_category,
        search=search,
        hundred_percent_bodyweight=hundred_percent_bodyweight,
        is_custom=is_custom,
        use_profile=use_profile,
        user_id=user_id,
    )


@router.get(
    "/{exercise_id}",
    response_model=ExerciseResponse,
    summary="Get a single exercise by ID",
)
@limiter.limit("60/minute")  # read
def get_exercise_by_id(
    request: Request,
    exercise_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the full details of a single exercise including secondary muscles."""
    return service.get_exercise(db, exercise_id)


# ──────────────────────────────────────────
# Admin-only endpoints
# ──────────────────────────────────────────

@router.post(
    "/",
    response_model=ExerciseResponse,
    status_code=201,
    summary="[Admin] Create a new exercise",
)
@limiter.limit("30/minute")  # write mutation
def create_exercise(
    request: Request,
    data: ExerciseCreate,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Create a new exercise in the library.
    Secondary muscles are passed as a list of strings in `secondary_muscles`.
    """
    return service.create_exercise(db, data)


@router.put(
    "/{exercise_id}",
    response_model=ExerciseResponse,
    summary="[Admin] Update an exercise",
)
@limiter.limit("30/minute")  # write mutation
def update_exercise(
    request: Request,
    exercise_id: uuid.UUID,
    data: ExerciseUpdate,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Partially update an exercise. Only fields that are sent will be changed.
    Pass `secondary_muscles: []` to clear all secondary muscles,
    or omit the field entirely to leave them unchanged.
    """
    return service.update_exercise(db, exercise_id, data)


@router.delete(
    "/{exercise_id}",
    summary="[Admin] Archive (soft-delete) an exercise",
)
@limiter.limit("30/minute")  # write mutation
def delete_exercise(
    request: Request,
    exercise_id: uuid.UUID,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Soft-deletes an exercise by setting is_archived=True.
    It will no longer appear in listings but is not removed from the database.
    """
    return service.delete_exercise(db, exercise_id)