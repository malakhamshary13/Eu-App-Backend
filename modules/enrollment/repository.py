import uuid
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from modules.enrollment.models import UserPlanEnrollment
from modules.enrollment.schemas import (
    ENROLLMENT_TRANSITIONS,
    EnrollmentCreate,
    EnrollmentStatusUpdate,
)


class EnrollmentRepository:
    """
    DB operations for plans.user_plan_enrollments.

    Invariants enforced (medical-grade rules):
      1. A user can have at most ONE 'active' enrollment per plan type
         (workout or meal) at any given time.  Enrolling while already active
         in the same plan type returns a 409 — the client must drop/complete
         the existing enrollment first.
      2. Status transitions are forward-only per the ENROLLMENT_TRANSITIONS map.
      3. 'completed' and 'dropped' are terminal — no further changes allowed.
      4. Enrollments cannot be hard-deleted once completed (permanent records).
         Only 'scheduled'/'paused'/'active' (non-completed) can be removed.
    """

    # ──────────────────────────────────────────────────────────────────────────
    # Guards
    # ──────────────────────────────────────────────────────────────────────────

    def _get_enrollment_or_404(
        self, db: Session, enrollment_id: uuid.UUID, user_id: uuid.UUID
    ) -> UserPlanEnrollment:
        enrollment = (
            db.query(UserPlanEnrollment)
            .filter(
                UserPlanEnrollment.id == enrollment_id,
                UserPlanEnrollment.user_id == user_id,
            )
            .first()
        )
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Enrollment {enrollment_id} not found.",
            )
        return enrollment

    def _check_no_active_conflict(
        self,
        db: Session,
        user_id: uuid.UUID,
        workout_plan_id: Optional[uuid.UUID],
        meal_plan_id: Optional[uuid.UUID],
    ) -> None:
        """
        Prevent duplicate active enrollments in the same plan type.
        A user must drop/complete their current enrollment before joining another.
        """
        if workout_plan_id:
            conflict = (
                db.query(UserPlanEnrollment)
                .filter(
                    UserPlanEnrollment.user_id == user_id,
                    UserPlanEnrollment.workout_plan_id.isnot(None),
                    UserPlanEnrollment.status == "active",
                )
                .first()
            )
            if conflict:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"You already have an active workout-plan enrollment "
                        f"(id={conflict.id}). "
                        "Drop or complete it before enrolling in a new plan."
                    ),
                )

        if meal_plan_id:
            conflict = (
                db.query(UserPlanEnrollment)
                .filter(
                    UserPlanEnrollment.user_id == user_id,
                    UserPlanEnrollment.meal_plan_id.isnot(None),
                    UserPlanEnrollment.status == "active",
                )
                .first()
            )
            if conflict:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"You already have an active meal-plan enrollment "
                        f"(id={conflict.id}). "
                        "Drop or complete it before enrolling in a new plan."
                    ),
                )

    # ──────────────────────────────────────────────────────────────────────────
    # Create
    # ──────────────────────────────────────────────────────────────────────────

    def create_enrollment(
        self,
        db: Session,
        user_id: uuid.UUID,
        data: EnrollmentCreate,
    ) -> UserPlanEnrollment:
        self._check_no_active_conflict(
            db, user_id, data.workout_plan_id, data.meal_plan_id
        )
        enrollment = UserPlanEnrollment(
            user_id=user_id,
            workout_plan_id=data.workout_plan_id,
            meal_plan_id=data.meal_plan_id,
            status="active",
        )
        db.add(enrollment)
        db.commit()
        db.refresh(enrollment)
        return enrollment

    # ──────────────────────────────────────────────────────────────────────────
    # Read
    # ──────────────────────────────────────────────────────────────────────────

    def list_enrollments(
        self,
        db: Session,
        user_id: uuid.UUID,
        enroll_status: Optional[str] = None,
    ) -> List[UserPlanEnrollment]:
        q = db.query(UserPlanEnrollment).filter(
            UserPlanEnrollment.user_id == user_id
        )
        if enroll_status:
            q = q.filter(UserPlanEnrollment.status == enroll_status)
        return q.order_by(UserPlanEnrollment.enrolled_at.desc()).all()

    def get_enrollment(
        self, db: Session, enrollment_id: uuid.UUID, user_id: uuid.UUID
    ) -> UserPlanEnrollment:
        return self._get_enrollment_or_404(db, enrollment_id, user_id)

    def get_active_workout_enrollment(
        self, db: Session, user_id: uuid.UUID
    ) -> Optional[UserPlanEnrollment]:
        return (
            db.query(UserPlanEnrollment)
            .filter(
                UserPlanEnrollment.user_id == user_id,
                UserPlanEnrollment.workout_plan_id.isnot(None),
                UserPlanEnrollment.status == "active",
            )
            .first()
        )

    def get_active_meal_enrollment(
        self, db: Session, user_id: uuid.UUID
    ) -> Optional[UserPlanEnrollment]:
        return (
            db.query(UserPlanEnrollment)
            .filter(
                UserPlanEnrollment.user_id == user_id,
                UserPlanEnrollment.meal_plan_id.isnot(None),
                UserPlanEnrollment.status == "active",
            )
            .first()
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Update status
    # ──────────────────────────────────────────────────────────────────────────

    def update_status(
        self,
        db: Session,
        enrollment_id: uuid.UUID,
        user_id: uuid.UUID,
        data: EnrollmentStatusUpdate,
    ) -> UserPlanEnrollment:
        enrollment = self._get_enrollment_or_404(db, enrollment_id, user_id)
        current = enrollment.status
        target  = data.status

        allowed = ENROLLMENT_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Cannot transition enrollment from '{current}' to '{target}'. "
                    f"Allowed next states: {sorted(allowed) or 'none (terminal)'}."
                ),
            )

        enrollment.status = target
        db.commit()
        db.refresh(enrollment)
        return enrollment

    # ──────────────────────────────────────────────────────────────────────────
    # Delete
    # ──────────────────────────────────────────────────────────────────────────

    def delete_enrollment(
        self, db: Session, enrollment_id: uuid.UUID, user_id: uuid.UUID
    ) -> dict:
        enrollment = self._get_enrollment_or_404(db, enrollment_id, user_id)
        if enrollment.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Completed enrollments are permanent records and cannot be deleted. "
                    "Use status PATCH to drop an active enrollment instead."
                ),
            )
        db.delete(enrollment)
        db.commit()
        return {"detail": f"Enrollment {enrollment_id} deleted."}
