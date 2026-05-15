import uuid
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from modules.workouts.models import WorkoutPlan, WorkoutPlanRoutine, RoutineExercise
from modules.workouts.schemas import (
    WorkoutPlanCreate, WorkoutPlanUpdate,
    CreateRoutineInPlan, RoutineExerciseCreate,
)


class WorkoutRepository:
    """All DB operations for the workouts module."""

    # ──────────────────────────────────────────
    # Guards
    # ──────────────────────────────────────────

    def _require_owner(self, plan: WorkoutPlan, user_id: uuid.UUID) -> None:
        if plan.created_by != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You do not own this workout plan.",
            )

    def _get_plan_or_404(self, db: Session, plan_id: uuid.UUID) -> WorkoutPlan:
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workout plan {plan_id} not found.",
            )
        return plan

    def _get_routine_or_404(self, db: Session, routine_id: uuid.UUID) -> WorkoutPlanRoutine:
        routine = db.query(WorkoutPlanRoutine).filter(WorkoutPlanRoutine.id == routine_id).first()
        if not routine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Routine {routine_id} not found.",
            )
        return routine

    # ──────────────────────────────────────────
    # Read
    # ──────────────────────────────────────────

    def get_my_plans(self, db: Session, user_id: uuid.UUID) -> List[WorkoutPlan]:
        """Return all personal (non-template) plans owned by this user."""
        return (
            db.query(WorkoutPlan)
            .filter(
                WorkoutPlan.created_by == user_id,
                WorkoutPlan.is_template.is_(False),
            )
            .order_by(WorkoutPlan.title)
            .all()
        )

    def get_plan_by_id(
        self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkoutPlan:
        """Return a plan by ID. Raises 403 if the user doesn't own it."""
        plan = self._get_plan_or_404(db, plan_id)
        self._require_owner(plan, user_id)
        return plan

    def get_routine_by_id(
        self, db: Session, routine_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkoutPlanRoutine:
        """
        Return a routine (workout_plan_routine) with its exercises.
        Ownership is checked via the parent plan.
        """
        routine = self._get_routine_or_404(db, routine_id)
        # Verify the parent plan belongs to this user (or is a template)
        plan = self._get_plan_or_404(db, routine.workout_plan_id)
        if not plan.is_template:
            self._require_owner(plan, user_id)
        return routine

    # ──────────────────────────────────────────
    # Create — Plan
    # ──────────────────────────────────────────

    def create_plan(
        self, db: Session, user_id: uuid.UUID, data: WorkoutPlanCreate
    ) -> WorkoutPlan:
        """Create an empty workout plan (no routines yet)."""
        plan = WorkoutPlan(
            title=data.title,
            difficulty_level=data.difficulty_level,
            schedule_type=data.schedule_type,
            description=data.description,
            start_date=data.start_date,
            end_date=data.end_date,
            is_template=False,
            created_by=user_id,
            creator_role='user',
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return plan

    # ──────────────────────────────────────────
    # Create — Routine
    # ──────────────────────────────────────────

    def create_routine_for_plan(
        self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID,
        data: CreateRoutineInPlan,
    ) -> WorkoutPlanRoutine:
        """
        Create a new routine row directly on the plan (owner only).
        name/description live on workout_plan_routines — no separate table.
        """
        self.get_plan_by_id(db, plan_id, user_id)  # ownership check

        routine = WorkoutPlanRoutine(
            workout_plan_id=plan_id,
            name=data.name if not data.is_rest_day else None,
            description=data.description if not data.is_rest_day else None,
            day_number=data.day_number,
            day_of_week=data.day_of_week,
            is_rest_day=data.is_rest_day,
            position=data.position,
        )
        db.add(routine)
        db.commit()
        db.refresh(routine)
        return routine

    # ──────────────────────────────────────────
    # Create — Routine Exercise
    # ──────────────────────────────────────────

    def add_exercise_to_routine(
        self, db: Session, routine_id: uuid.UUID, user_id: uuid.UUID,
        data: RoutineExerciseCreate,
    ) -> RoutineExercise:
        """
        Add a single exercise to an existing routine (owner only).
        Returns the new entry with full exercise details loaded.
        """
        routine = self.get_routine_by_id(db, routine_id, user_id)  # ownership check

        entry = RoutineExercise(
            workout_plan_routine_id=routine.id,
            exercise_id=data.exercise_id,
            position=data.position,
            sets=data.sets,
            reps=data.reps,
            weight_kg=data.weight_kg,
            rest_time_seconds=data.rest_time_seconds,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    # ──────────────────────────────────────────
    # Update
    # ──────────────────────────────────────────

    def update_plan(
        self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID,
        data: WorkoutPlanUpdate,
    ) -> WorkoutPlan:
        """Partially update plan metadata (owner only)."""
        plan = self.get_plan_by_id(db, plan_id, user_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(plan, field, value)
        db.commit()
        db.refresh(plan)
        return plan

    # ──────────────────────────────────────────
    # Delete
    # ──────────────────────────────────────────

    def delete_plan(
        self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID
    ) -> dict:
        """Delete a workout plan and all its routines/exercises (owner only)."""
        plan = self.get_plan_by_id(db, plan_id, user_id)
        db.delete(plan)
        db.commit()
        return {"message": f"Workout plan '{plan.title}' deleted."}

    def delete_routine(
        self, db: Session, routine_id: uuid.UUID, user_id: uuid.UUID
    ) -> dict:
        """Delete a routine slot and all its exercises (owner only)."""
        routine = self.get_routine_by_id(db, routine_id, user_id)
        name = routine.name or "Rest day"
        db.delete(routine)
        db.commit()
        return {"message": f"Routine '{name}' deleted."}
