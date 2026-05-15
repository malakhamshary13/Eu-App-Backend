import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from core.auth import get_current_user
from core.limiter import limiter
from db.database import get_db
from modules.rehab_tracking.schemas import (
    ExerciseProgressResponse,
    RehabHistoryResponse,
    RehabSessionCreate,
    RehabSessionDetailResponse,
    RehabSessionListResponse,
    RehabSessionResponse,
    RehabSessionStatusUpdate,
    RehabStreaksResponse,
    SessionExerciseResponse,
    SessionExerciseUpdate,
)
from modules.rehab_tracking.service import RehabTrackingService

router = APIRouter(prefix="/tracker/rehab", tags=["Rehab Tracking"])
service = RehabTrackingService()


# ─────────────────────────────────────────────────────────────────────────────
# Sessions
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/sessions",
    response_model=RehabSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a rehab session",
)
@limiter.limit("20/minute")
def create_session(
    request: Request,
    data: RehabSessionCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new rehab session linked to a **plan** and one of its **routines**.

    Exercise logs are **auto-created** from the routine's prescription —
    one `session_exercise` row per `rehab_routine_exercise` in the routine.
    Update each exercise's actual performance via
    `PATCH /tracker/rehab/sessions/{session_id}/exercises/{entry_id}`.

    **Status on creation:**
    - `"scheduled"` — plan for a future date (default).
    - `"in_progress"` — start immediately (sets `started_at` to now).
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.create_session(db, user_id, data)


@router.get(
    "/sessions",
    response_model=RehabSessionListResponse,
    summary="List my rehab sessions",
)
@limiter.limit("30/minute")
def list_sessions(
    request: Request,
    session_status: Optional[str] = Query(
        None,
        alias="status",
        pattern="^(scheduled|in_progress|completed|skipped)$",
        description="Filter by session status.",
    ),
    from_date: Optional[date] = Query(None, description="Earliest scheduled_date (inclusive)."),
    to_date:   Optional[date] = Query(None, description="Latest scheduled_date (inclusive)."),
    plan_id:   Optional[uuid.UUID] = Query(None, description="Filter by linked rehab plan."),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return all rehab sessions for the authenticated user, ordered by
    `scheduled_date` descending. Use `status`, `from_date`, `to_date`,
    and `plan_id` to narrow results.
    """
    user_id = uuid.UUID(str(current_user.id))
    sessions = service.list_sessions(db, user_id, session_status, from_date, to_date, plan_id)
    return RehabSessionListResponse(total=len(sessions), results=sessions)


@router.get(
    "/sessions/{session_id}",
    response_model=RehabSessionResponse,
    summary="Get a rehab session with all exercise logs",
)
@limiter.limit("30/minute")
def get_session(
    request: Request,
    session_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the full session including every exercise log."""
    user_id = uuid.UUID(str(current_user.id))
    return service.get_session(db, session_id, user_id)


@router.patch(
    "/sessions/{session_id}/status",
    response_model=RehabSessionResponse,
    summary="Advance session status (start / complete / skip)",
)
@limiter.limit("20/minute")
def update_session_status(
    request: Request,
    session_id: uuid.UUID,
    data: RehabSessionStatusUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Advance the session lifecycle. Transitions are **forward-only**:

    | Current | Allowed next |
    |---|---|
    | `scheduled` | `in_progress`, `skipped` |
    | `in_progress` | `completed` |
    | `completed` / `skipped` | *(terminal)* |

    **Completing requires ≥ 1 exercise marked `is_completed = true`.**
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
    Delete a session and all its exercise logs.
    **Completed sessions are permanent records — returns 409.**
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.delete_session(db, session_id, user_id)


# ─────────────────────────────────────────────────────────────────────────────
# Session Exercises (performance logging)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/sessions/{session_id}/exercises",
    response_model=List[SessionExerciseResponse],
    summary="Get all exercise logs for a session",
)
@limiter.limit("30/minute")
def get_session_exercises(
    request: Request,
    session_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return every exercise log for the session with exercise details embedded."""
    user_id = uuid.UUID(str(current_user.id))
    return service.get_session_exercises(db, session_id, user_id)


@router.patch(
    "/sessions/{session_id}/exercises/{entry_id}",
    response_model=SessionExerciseResponse,
    summary="Log / update performance for a single exercise",
)
@limiter.limit("60/minute")
def update_session_exercise(
    request: Request,
    session_id: uuid.UUID,
    entry_id: uuid.UUID,
    data: SessionExerciseUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Record actual performance for one exercise. Only sent fields are updated.

    | Field | Notes |
    |---|---|
    | `sets_completed` | Actual sets done |
    | `reps_completed` | Actual reps done |
    | `hold_time_seconds` | Actual hold for isometric exercises |
    | `is_completed` | `true` when user finishes this exercise |
    | `pain_level` | 1–10 exercise-level pain rating |
    | `notes` | Free-text notes |

    **Session must be `in_progress`** — returns **409** otherwise.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.update_session_exercise(db, session_id, entry_id, user_id, data)


# ─────────────────────────────────────────────────────────────────────────────
# Analytics — backed by DB stored procedures
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/streaks",
    response_model=RehabStreaksResponse,
    summary="Get my rehab streak stats",
)
@limiter.limit("30/minute")
def get_streaks(
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the user's rehab consistency streaks.

    Powered by `tracker.get_rehab_streaks()`.

    | Field | Description |
    |---|---|
    | `current_streak` | Consecutive days with a completed session |
    | `longest_streak` | All-time longest streak |
    | `last_active_day` | Date of the most recent completed session |
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.get_streaks(db, user_id)


@router.get(
    "/sessions/{session_id}/detail",
    response_model=RehabSessionDetailResponse,
    summary="Get rich session detail — planned vs. actual",
)
@limiter.limit("30/minute")
def get_session_detail(
    request: Request,
    session_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns full session detail with planned vs. actual comparison per exercise.

    Powered by `tracker.get_rehab_session_detail(p_session_id)`.

    Includes planned prescription (`planned_sets`, `planned_reps`, `planned_hold_seconds`)
    alongside actual logged values, completion status, and pain ratings.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.get_session_detail(db, session_id, user_id)


@router.get(
    "/exercises/{exercise_id}/progress",
    response_model=ExerciseProgressResponse,
    summary="Get progress timeline for a single exercise",
)
@limiter.limit("30/minute")
def get_exercise_progress(
    request: Request,
    exercise_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns a chronological timeline of every time the user performed
    a specific rehab exercise across all sessions.

    Powered by `tracker.get_rehab_exercise_progress(p_exercise_id)`.

    Use this to visualise **recovery progress** — improving reps, decreasing
    pain level, or extending hold times over sessions.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.get_exercise_progress(db, exercise_id, user_id)


@router.get(
    "/history",
    response_model=RehabHistoryResponse,
    summary="Get full rehab session history (completed only)",
)
@limiter.limit("20/minute")
def get_history(
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns all **completed** rehab sessions with full exercise breakdown,
    ordered by `scheduled_date` descending.

    Powered by `tracker.get_rehab_completed_sessions()`.

    Each entry includes session metadata, `total_exercises` / `exercises_completed`
    aggregates, and per-exercise actual performance with pain ratings.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.get_history(db, user_id)
