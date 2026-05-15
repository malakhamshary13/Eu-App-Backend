import uuid
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from modules.rehab.models import (
    RehabCondition, RehabExercise, RehabConditionMapping,
    RehabPlan, RehabRoutine, RehabRoutineExercise,
)
from modules.rehab.schemas import (
    RehabPlanCreate, RehabPlanUpdate,
    RehabRoutineCreate, RehabRoutineUpdate,
    RehabRoutineExerciseCreate,
    SetRehabConditionRequest,
)
from modules.users.models import HealthProfile


class RehabRepository:
    """All DB operations for the rehab module."""

    # ──────────────────────────────────────────
    # Guards / helpers
    # ──────────────────────────────────────────

    def _get_plan_or_404(self, db: Session, plan_id: uuid.UUID) -> RehabPlan:
        plan = db.query(RehabPlan).filter(RehabPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rehab plan {plan_id} not found.",
            )
        return plan

    def _require_plan_owner(self, plan: RehabPlan, user_id: uuid.UUID) -> None:
        if plan.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You do not own this rehab plan.",
            )

    def _get_routine_or_404(self, db: Session, routine_id: uuid.UUID) -> RehabRoutine:
        routine = db.query(RehabRoutine).filter(RehabRoutine.id == routine_id).first()
        if not routine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rehab routine {routine_id} not found.",
            )
        return routine

    def _get_routine_exercise_or_404(
        self, db: Session, entry_id: uuid.UUID
    ) -> RehabRoutineExercise:
        entry = db.query(RehabRoutineExercise).filter(RehabRoutineExercise.id == entry_id).first()
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Routine exercise {entry_id} not found.",
            )
        return entry

    # ──────────────────────────────────────────
    # Endpoint 1 — GET exercises for a rehab user
    # ──────────────────────────────────────────

    def get_exercises_for_rehab_user(
        self, db: Session, user_id: uuid.UUID
    ) -> List[RehabExercise]:
        """
        Return all rehab exercises linked to the user's active rehab condition.
        Falls back to ALL rehab exercises if the user has no condition set.
        """
        # Look up the user's active condition via health_profile
        health = db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()

        # Try to find the condition_id stored on the user's active rehab plan
        active_plan = (
            db.query(RehabPlan)
            .filter(RehabPlan.user_id == user_id, RehabPlan.is_active.is_(True))
            .order_by(RehabPlan.created_at.desc())
            .first()
        )

        condition_id: Optional[uuid.UUID] = active_plan.condition_id if active_plan else None

        if condition_id:
            # Return only exercises mapped to this condition
            mappings = (
                db.query(RehabConditionMapping)
                .filter(RehabConditionMapping.condition_id == condition_id)
                .all()
            )
            exercise_ids = [m.exercise_id for m in mappings]
            if exercise_ids:
                return (
                    db.query(RehabExercise)
                    .filter(RehabExercise.id.in_(exercise_ids))
                    .order_by(RehabExercise.title)
                    .all()
                )

        # No condition — return all rehab exercises
        return db.query(RehabExercise).order_by(RehabExercise.title).all()

    # ──────────────────────────────────────────
    # Endpoint 2 — PUT user's rehab condition
    # ──────────────────────────────────────────

    def set_rehab_condition(
        self, db: Session, user_id: uuid.UUID, data: SetRehabConditionRequest
    ) -> HealthProfile:
        """
        Set or clear the rehab condition on the user's health profile.
        Also writes injury_details and recovery_stage if provided.
        """

        if data.condition_id:
            condition = db.query(RehabCondition).filter(
                RehabCondition.id == data.condition_id
            ).first()
            if not condition:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Rehab condition {data.condition_id} not found.",
                )

        health = db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()

        if not health:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Health profile not found. "
                    "Create one first via POST /auth/health-profile."
                ),
            )

        if data.injury_details is not None:
            health.injury_details = data.injury_details
        if data.recovery_stage is not None:
            health.recovery_stage = data.recovery_stage

        db.commit()
        db.refresh(health)
        return health

    # ──────────────────────────────────────────
    # Endpoint 3 — Rehab Plan CRUD
    # ──────────────────────────────────────────

    def list_my_plans(self, db: Session, user_id: uuid.UUID) -> List[RehabPlan]:
        """Return all rehab plans owned by this user."""
        return (
            db.query(RehabPlan)
            .filter(RehabPlan.user_id == user_id)
            .order_by(RehabPlan.created_at.desc())
            .all()
        )

    def get_plan(
        self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID
    ) -> RehabPlan:
        plan = self._get_plan_or_404(db, plan_id)
        self._require_plan_owner(plan, user_id)
        return plan

    def create_plan(
        self, db: Session, user_id: uuid.UUID, data: RehabPlanCreate
    ) -> RehabPlan:
        """Create a new rehab plan (no routines yet)."""
        if data.condition_id:
            condition = db.query(RehabCondition).filter(
                RehabCondition.id == data.condition_id
            ).first()
            if not condition:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Rehab condition {data.condition_id} not found.",
                )

        plan = RehabPlan(
            user_id=user_id,
            condition_id=data.condition_id,
            title=data.title,
            description=data.description,
            is_active=True,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return plan

    def update_plan(
        self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID, data: RehabPlanUpdate
    ) -> RehabPlan:
        """Partially update a rehab plan (owner only)."""
        plan = self.get_plan(db, plan_id, user_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(plan, field, value)
        db.commit()
        db.refresh(plan)
        return plan

    def delete_plan(
        self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID
    ) -> dict:
        """Delete a rehab plan and all its routines/exercises (owner only)."""
        plan = self.get_plan(db, plan_id, user_id)
        title = plan.title
        db.delete(plan)
        db.commit()
        return {"message": f"Rehab plan '{title}' deleted."}

    # ──────────────────────────────────────────
    # Routine CRUD
    # ──────────────────────────────────────────

    def create_routine(
        self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID, data: RehabRoutineCreate
    ) -> RehabRoutine:
        """Add a new routine to an existing plan (plan owner only)."""
        self.get_plan(db, plan_id, user_id)  # ownership check

        routine = RehabRoutine(
            plan_id=plan_id,
            name=data.name,
            order_index=data.order_index,
        )
        db.add(routine)
        db.commit()
        db.refresh(routine)
        return routine

    def update_routine(
        self, db: Session, routine_id: uuid.UUID, user_id: uuid.UUID, data: RehabRoutineUpdate
    ) -> RehabRoutine:
        """Update a routine's name or order (plan owner only)."""
        routine = self._get_routine_or_404(db, routine_id)
        self.get_plan(db, routine.plan_id, user_id)   # ownership check via parent plan

        for field, value in data.model_dump(exclude_none=True).items():
            setattr(routine, field, value)
        db.commit()
        db.refresh(routine)
        return routine

    def delete_routine(
        self, db: Session, routine_id: uuid.UUID, user_id: uuid.UUID
    ) -> dict:
        """Delete a routine and all its exercises (plan owner only)."""
        routine = self._get_routine_or_404(db, routine_id)
        self.get_plan(db, routine.plan_id, user_id)   # ownership check

        name = routine.name
        db.delete(routine)
        db.commit()
        return {"message": f"Rehab routine '{name}' deleted."}

    # ──────────────────────────────────────────
    # Routine Exercise CRUD
    # ──────────────────────────────────────────

    def add_exercise_to_routine(
        self,
        db: Session,
        routine_id: uuid.UUID,
        user_id: uuid.UUID,
        data: RehabRoutineExerciseCreate,
    ) -> RehabRoutineExercise:
        """Add a single exercise to a routine (plan owner only)."""
        routine = self._get_routine_or_404(db, routine_id)
        self.get_plan(db, routine.plan_id, user_id)   # ownership check

        exercise = db.query(RehabExercise).filter(RehabExercise.id == data.exercise_id).first()
        if not exercise:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rehab exercise {data.exercise_id} not found in library.",
            )

        entry = RehabRoutineExercise(
            routine_id=routine_id,
            exercise_id=data.exercise_id,
            sets=data.sets,
            reps=data.reps,
            hold_time_seconds=data.hold_time_seconds,
            rest_seconds=data.rest_seconds,
            notes=data.notes,
            order_index=data.order_index,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    def delete_routine_exercise(
        self, db: Session, entry_id: uuid.UUID, user_id: uuid.UUID
    ) -> dict:
        """Remove an exercise from a routine (plan owner only)."""
        entry = self._get_routine_exercise_or_404(db, entry_id)
        routine = self._get_routine_or_404(db, entry.routine_id)
        self.get_plan(db, routine.plan_id, user_id)   # ownership check

        db.delete(entry)
        db.commit()
        return {"message": "Exercise removed from routine."}

    # ──────────────────────────────────────────
    # Condition library helpers
    # ──────────────────────────────────────────

    def list_conditions(self, db: Session) -> List[RehabCondition]:
        """Return all available rehab conditions from the library."""
        return db.query(RehabCondition).order_by(RehabCondition.name).all()
