import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from core.auth import get_current_user
from core.limiter import limiter
from db.database import get_db
from modules.workout_tracking.schemas import (
    SessionCreate,
    SessionItemBulkCreate,
    SessionItemCreate,
    SessionItemResponse,
    SessionItemUpdate,
    SessionListResponse,
    SessionResponse,
    SessionStatusUpdate,
)
from modules.workout_tracking.service import WorkoutTrackingService

router = APIRouter(prefix="/tracker/workouts", tags=["Workout Tracking"])
service = WorkoutTrackingService()


# ─────────────────────────────────────────────────────────────────────────────
# Sessions
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a workout session",
)
@limiter.limit("20/minute")
def create_session(
    request: Request,
    data: SessionCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new workout session.

    **Status on creation:**
    - `"scheduled"` — plan it for a future date (default).
    - `"in_progress"` — start immediately (sets `started_at` to now).

    Optionally link to a `workout_plan_id` and `routine_id` from the plans
    module so the session knows which plan/day it belongs to.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.create_session(db, user_id, data)


@router.get(
    "/sessions",
    response_model=SessionListResponse,
    summary="List my workout sessions",
)
@limiter.limit("30/minute")
def list_sessions(
    request: Request,
    session_status: Optional[str] = Query(
        None,
        alias="status",
        pattern="^(scheduled|in_progress|completed|abandoned|skipped)$",
        description="Filter by session status.",
    ),
    from_date: Optional[date] = Query(None, description="Earliest scheduled_date (inclusive)."),
    to_date: Optional[date] = Query(None, description="Latest scheduled_date (inclusive)."),
    workout_plan_id: Optional[uuid.UUID] = Query(None, description="Filter by linked workout plan."),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return all workout sessions for the authenticated user, ordered by
    `scheduled_date` descending (most recent first).

    Use `status`, `from_date`, `to_date`, and `workout_plan_id` to narrow results.
    """
    user_id = uuid.UUID(str(current_user.id))
    sessions = service.list_sessions(
        db, user_id, session_status, from_date, to_date, workout_plan_id
    )
    return SessionListResponse(total=len(sessions), results=sessions)


@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    summary="Get a session with all logged sets",
)
@limiter.limit("30/minute")
def get_session(
    request: Request,
    session_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return the full session including every logged set (`items`), sorted by
    exercise then set number.  Raises **404** if not found or not owned by caller.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.get_session(db, session_id, user_id)


@router.patch(
    "/sessions/{session_id}/status",
    response_model=SessionResponse,
    summary="Advance session status (start / complete / abandon / skip)",
)
@limiter.limit("20/minute")
def update_session_status(
    request: Request,
    session_id: uuid.UUID,
    data: SessionStatusUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Advance the session through its lifecycle.  Transitions are **forward-only**:

    | Current state | Allowed next states |
    |---|---|
    | `scheduled` | `in_progress`, `skipped` |
    | `in_progress` | `completed`, `abandoned` |
    | `completed` | *(terminal — immutable)* |
    | `abandoned` | *(terminal — immutable)* |
    | `skipped` | *(terminal — immutable)* |

    **Completing a session with zero logged sets is rejected (422).**

    Pass `completed_at` in the body only when transitioning to `"completed"`;
    it defaults to the server's current UTC time if omitted.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.update_session_status(db, session_id, user_id, data)


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a session (non-completed only)",
)
@limiter.limit("10/minute")
def delete_session(
    request: Request,
    session_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a session and all its logged sets.
    **Completed sessions are permanent records and cannot be deleted.**
    Returns **409** if you try to delete a completed session.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.delete_session(db, session_id, user_id)


# ─────────────────────────────────────────────────────────────────────────────
# Session Items (sets)
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/sessions/{session_id}/items",
    response_model=SessionItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log a single set",
)
@limiter.limit("60/minute")
def log_set(
    request: Request,
    session_id: uuid.UUID,
    data: SessionItemCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Log **one set** of one exercise within an `in_progress` session.

    **Rules:**
    - `set_number` must be ≥ 1.
    - `reps_completed` and `weight_used` must be ≥ 0 (0 is valid for bodyweight
      exercises or to mark a failed set attempt).
    - The same `(exercise_id, set_number)` pair cannot appear twice in the same
      session — returns **409** if a duplicate is detected.
    - The session must be `in_progress` — returns **409** otherwise.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.log_set(db, session_id, user_id, data)


@router.post(
    "/sessions/{session_id}/items/bulk",
    response_model=List[SessionItemResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk-log all sets of one exercise",
)
@limiter.limit("30/minute")
def log_sets_bulk(
    request: Request,
    session_id: uuid.UUID,
    data: SessionItemBulkCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Log **all sets of a single exercise** in one atomic request.

    Useful when the user completes multiple sets before recording — e.g. 4 sets
    of Bench Press all at once.

    **Rules (same as single-set logging, applied to all rows):**
    - All `set_number` values in the request must be unique.
    - None may conflict with sets already recorded for this exercise in this session.
    - Session must be `in_progress`.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.log_sets_bulk(
        db, session_id, user_id, data.exercise_id, data.sets
    )


@router.get(
    "/sessions/{session_id}/items",
    response_model=List[SessionItemResponse],
    summary="Get all logged sets for a session",
)
@limiter.limit("30/minute")
def get_session_items(
    request: Request,
    session_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return every logged set for the session, ordered by `exercise_id` then
    `set_number`.  Full exercise detail is embedded in each item.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.get_session_items(db, session_id, user_id)


@router.patch(
    "/sessions/{session_id}/items/{item_id}",
    response_model=SessionItemResponse,
    summary="Correct a logged set",
)
@limiter.limit("30/minute")
def update_set(
    request: Request,
    session_id: uuid.UUID,
    item_id: uuid.UUID,
    data: SessionItemUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Partially update a previously logged set — e.g. fix reps/weight or mark it
    as completed.  Only provided (non-null) fields are changed.

    **Session must be `in_progress`** — returns **409** for terminal sessions.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.update_set(db, session_id, item_id, user_id, data)


@router.delete(
    "/sessions/{session_id}/items/{item_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove a logged set",
)
@limiter.limit("30/minute")
def delete_set(
    request: Request,
    session_id: uuid.UUID,
    item_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a single set from an `in_progress` session.
    Returns **409** if the session is no longer in progress.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.delete_set(db, session_id, item_id, user_id)
