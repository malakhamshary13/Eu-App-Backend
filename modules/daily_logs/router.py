import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from core.auth import get_current_user
from core.limiter import limiter
from db.database import get_db
from modules.daily_logs.schemas import (
    DailyLogListResponse,
    DailyLogResponse,
    DailyLogUpdate,
    DailyLogUpsert,
)
from modules.daily_logs.service import DailyLogService

router = APIRouter(prefix="/tracker/daily", tags=["Daily Logs"])
service = DailyLogService()


@router.post(
    "/",
    response_model=DailyLogResponse,
    status_code=status.HTTP_200_OK,   # 200 because it's an upsert (may update)
    summary="Create or update today's daily log",
)
@limiter.limit("20/minute")
def upsert_daily_log(
    request: Request,
    data: DailyLogUpsert,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    **Upsert** (create or update) the daily log for a given `date`.

    - If no log exists for that date, it is created.
    - If one already exists, only the non-null fields you supply are updated
      — omitted fields remain unchanged.

    **Fields:**
    - `date` — the calendar day (required).
    - `calories_consumed` — total kcal consumed that day (≥ 0).
    - `workouts_completed` — number of workout sessions finished (≥ 0).
    - `recovery_notes` — free-text wellbeing / physiotherapy notes.

    This endpoint is idempotent — calling it multiple times with the same
    `date` is safe.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.upsert_log(db, user_id, data)


@router.get(
    "/",
    response_model=DailyLogListResponse,
    summary="List daily logs (optionally filtered by date range)",
)
@limiter.limit("30/minute")
def list_daily_logs(
    request: Request,
    from_date: Optional[date] = Query(None, description="Start date (inclusive)."),
    to_date:   Optional[date] = Query(None, description="End date (inclusive)."),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return all daily logs for the authenticated user, ordered by date descending.
    Use `from_date` and `to_date` to narrow the window.

    Useful for displaying a calendar heat-map or progress chart.
    """
    user_id = uuid.UUID(str(current_user.id))
    logs = service.list_logs(db, user_id, from_date, to_date)
    return DailyLogListResponse(total=len(logs), results=logs)


@router.get(
    "/{log_date}",
    response_model=DailyLogResponse,
    summary="Get the log for a specific date",
)
@limiter.limit("30/minute")
def get_daily_log(
    request: Request,
    log_date: date,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return the daily log for `log_date`.
    Raises **404** if no log exists for that date.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.get_log_by_date(db, log_date, user_id)


@router.patch(
    "/{log_date}",
    response_model=DailyLogResponse,
    summary="Partially update an existing daily log",
)
@limiter.limit("20/minute")
def patch_daily_log(
    request: Request,
    log_date: date,
    data: DailyLogUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update only the fields you provide on an existing log.
    Raises **404** if no log exists for `log_date`.

    Use the `POST /` upsert endpoint if you're unsure whether the log
    already exists — it handles both cases automatically.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.patch_log(db, log_date, user_id, data)
