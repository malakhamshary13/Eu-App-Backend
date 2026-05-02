import uuid
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from modules.workouts.models import WorkoutPlan, Routine, RoutineExercise, WorkoutPlanRoutine
from modules.workouts.schemas import (
    WorkoutPlanCreate, WorkoutPlanUpdate,
    PlanRoutineSlotCreate, RoutineCreate,
)


class WorkoutRepository:
    """All DB operations for the workouts module."""

    # ──────────────────────────────────────────
    # Ownership guard
    # ──────────────────────────────────────────

    def _require_owner(self, plan: WorkoutPlan, user_id: uuid.UUID) -> None:
        """Raise 403 if the requesting user is not the plan owner."""
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

    # ──────────────────────────────────────────
    # Create
    # ──────────────────────────────────────────

    def _create_routine(
        self, db: Session, data: RoutineCreate, user_id: uuid.UUID
    ) -> Routine:
        """Insert a routine and its exercises. Returns the ORM object."""
        routine = Routine(
            name=data.name,
            description=data.description,
            created_by=user_id,
            is_template=False,
        )
        db.add(routine)
        db.flush()  # get routine.id

        for ex in data.exercises:
            db.add(RoutineExercise(
                routine_id=routine.id,
                exercise_id=ex.exercise_id,
                position=ex.position,
                sets=ex.sets,
                reps=ex.reps,
                weight_kg=ex.weight_kg,
                rest_time_seconds=ex.rest_time_seconds,
            ))
        return routine

    def _attach_slot(
        self,
        db: Session,
        plan_id: uuid.UUID,
        slot: PlanRoutineSlotCreate,
        user_id: uuid.UUID,
    ) -> WorkoutPlanRoutine:
        """Create a routine (if inline) and attach it as a slot to the plan."""
        routine_id = None

        if slot.is_rest_day:
            # Rest day — no routine needed
            pass
        elif slot.routine:
            # Inline routine creation
            routine = self._create_routine(db, slot.routine, user_id)
            routine_id = routine.id
        elif slot.routine_id:
            # Reference to an existing routine
            routine_id = slot.routine_id
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each slot must have a routine, routine_id, or is_rest_day=true.",
            )

        plan_routine = WorkoutPlanRoutine(
            workout_plan_id=plan_id,
            routine_id=routine_id,
            day_number=slot.day_number,
            day_of_week=slot.day_of_week,
            is_rest_day=slot.is_rest_day,
            position=slot.position,
        )
        db.add(plan_routine)
        return plan_routine

    def create_plan(
        self, db: Session, user_id: uuid.UUID, data: WorkoutPlanCreate
    ) -> WorkoutPlan:
        """Create a workout plan with all its routine slots."""
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
        db.flush()  # get plan.id

        for slot in data.slots:
            self._attach_slot(db, plan.id, slot, user_id)

        db.commit()
        db.refresh(plan)
        return plan

    # ──────────────────────────────────────────
    # Update
    # ──────────────────────────────────────────

    def update_plan(
        self,
        db: Session,
        plan_id: uuid.UUID,
        user_id: uuid.UUID,
        data: WorkoutPlanUpdate,
    ) -> WorkoutPlan:
        """Partially update plan metadata. Raises 403 if not owner."""
        plan = self.get_plan_by_id(db, plan_id, user_id)

        for field, value in data.model_dump(exclude_none=True).items():
            setattr(plan, field, value)

        db.commit()
        db.refresh(plan)
        return plan

    # ──────────────────────────────────────────
    # Routine slot management
    # ──────────────────────────────────────────

    def add_routine_slot(
        self,
        db: Session,
        plan_id: uuid.UUID,
        user_id: uuid.UUID,
        slot: PlanRoutineSlotCreate,
    ) -> WorkoutPlanRoutine:
        """Add a new routine slot to an existing plan (owner only)."""
        plan = self.get_plan_by_id(db, plan_id, user_id)   # ownership check inside
        pr = self._attach_slot(db, plan.id, slot, user_id)
        db.commit()
        db.refresh(pr)
        return pr

    def remove_routine_slot(
        self,
        db: Session,
        plan_id: uuid.UUID,
        slot_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict:
        """Remove a routine slot from a plan (owner only)."""
        self.get_plan_by_id(db, plan_id, user_id)  # ownership check

        slot = (
            db.query(WorkoutPlanRoutine)
            .filter(
                WorkoutPlanRoutine.id == slot_id,
                WorkoutPlanRoutine.workout_plan_id == plan_id,
            )
            .first()
        )
        if not slot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Routine slot not found in this plan.",
            )
        db.delete(slot)
        db.commit()
        return {"message": "Routine slot removed."}

    # ──────────────────────────────────────────
    # Delete
    # ──────────────────────────────────────────

    def delete_plan(
        self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID
    ) -> dict:
        """Delete a workout plan and all its slots (owner only)."""
        plan = self.get_plan_by_id(db, plan_id, user_id)
        db.delete(plan)
        db.commit()
        return {"message": f"Workout plan '{plan.title}' deleted."}
