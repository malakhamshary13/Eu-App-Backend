import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from core.auth import get_current_user
from core.limiter import limiter
from db.database import get_db
from modules.enrollment.schemas import (
    EnrollmentCreate,
    EnrollmentResponse,
    EnrollmentStatusUpdate,
)
from modules.enrollment.service import EnrollmentService

router = APIRouter(prefix="/enrollments", tags=["Plan Enrollments"])
service = EnrollmentService()


@router.post(
    "/",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll in a workout plan, meal plan, or both",
)
@limiter.limit("10/minute")
def create_enrollment(
    request: Request,
    data: EnrollmentCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Enroll the authenticated user in a plan.

    - Supply `workout_plan_id`, `meal_plan_id`, or both.
    - Returns **409** if the user is already **actively** enrolled in a plan
      of the same type — they must drop or complete the existing enrollment first.
    - The enrollment starts in `"active"` status.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.create_enrollment(db, user_id, data)


@router.get(
    "/",
    response_model=List[EnrollmentResponse],
    summary="List my plan enrollments",
)
@limiter.limit("30/minute")
def list_enrollments(
    request: Request,
    enroll_status: Optional[str] = Query(
        None,
        alias="status",
        pattern="^(active|paused|completed|dropped)$",
        description="Filter by enrollment status.",
    ),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return all enrollment records for the authenticated user,
    ordered by `enrolled_at` descending (most recent first).
    Use `?status=active` to see only current enrollments.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.list_enrollments(db, user_id, enroll_status)


@router.get(
    "/active/workout",
    response_model=EnrollmentResponse,
    summary="Get my currently active workout plan enrollment",
)
@limiter.limit("30/minute")
def get_active_workout_enrollment(
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the single active workout plan enrollment, or **404** if the
    user is not currently enrolled in any workout plan.

    Use this to determine which plan is driving the user's session schedule.
    """
    user_id = uuid.UUID(str(current_user.id))
    enrollment = service.get_active_workout_enrollment(db, user_id)
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active workout plan enrollment found.",
        )
    return enrollment


@router.get(
    "/active/meal",
    response_model=EnrollmentResponse,
    summary="Get my currently active meal plan enrollment",
)
@limiter.limit("30/minute")
def get_active_meal_enrollment(
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the single active meal plan enrollment, or **404** if the
    user is not currently enrolled in any meal plan.
    """
    user_id = uuid.UUID(str(current_user.id))
    enrollment = service.get_active_meal_enrollment(db, user_id)
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active meal plan enrollment found.",
        )
    return enrollment


@router.get(
    "/active/rehab",
    response_model=EnrollmentResponse,
    summary="Get my currently active rehab plan enrollment",
)
@limiter.limit("30/minute")
def get_active_rehab_enrollment(
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the single active rehab plan enrollment, or **404** if the
    user is not currently enrolled in any rehab plan.

    Use this on the dashboard to know which rehab plan is driving
    the user's current rehabilitation sessions.
    """
    user_id = uuid.UUID(str(current_user.id))
    enrollment = service.get_active_rehab_enrollment(db, user_id)
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active rehab plan enrollment found.",
        )
    return enrollment


@router.get(
    "/{enrollment_id}",
    response_model=EnrollmentResponse,
    summary="Get a specific enrollment by ID",
)
@limiter.limit("30/minute")
def get_enrollment(
    request: Request,
    enrollment_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return a single enrollment record. Raises **404** if not owned by caller."""
    user_id = uuid.UUID(str(current_user.id))
    return service.get_enrollment(db, enrollment_id, user_id)


@router.patch(
    "/{enrollment_id}/status",
    response_model=EnrollmentResponse,
    summary="Update enrollment status (pause / resume / complete / drop)",
)
@limiter.limit("20/minute")
def update_enrollment_status(
    request: Request,
    enrollment_id: uuid.UUID,
    data: EnrollmentStatusUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Advance the enrollment status. Transitions are **forward-only**:

    | Current | Allowed next states |
    |---|---|
    | `active` | `paused`, `completed`, `dropped` |
    | `paused` | `active` (resume), `dropped` |
    | `completed` | *(terminal)* |
    | `dropped` | *(terminal)* |

    Returns **409** for invalid transitions or terminal states.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.update_status(db, enrollment_id, user_id, data)


@router.delete(
    "/{enrollment_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an enrollment (non-completed only)",
)
@limiter.limit("10/minute")
def delete_enrollment(
    request: Request,
    enrollment_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Hard-delete an enrollment record. **Completed enrollments cannot be deleted**
    — they are permanent performance records. Returns **409** for completed.
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.delete_enrollment(db, enrollment_id, user_id)
