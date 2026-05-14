import uuid
from typing import List

from sqlalchemy.orm import Session

from modules.rehab.repository import RehabRepository
from modules.rehab.schemas import (
    RehabPlanCreate, RehabPlanUpdate,
    RehabRoutineCreate, RehabRoutineUpdate,
    RehabRoutineExerciseCreate,
    SetRehabConditionRequest,
)

_repo = RehabRepository()


class RehabService:
    """Business logic layer for the rehab module."""

    # ── Exercises ──────────────────────────────
    def get_exercises_for_user(self, db: Session, user_id: uuid.UUID):
        return _repo.get_exercises_for_rehab_user(db, user_id)

    # ── Condition setting ──────────────────────
    def set_rehab_condition(
        self, db: Session, user_id: uuid.UUID, data: SetRehabConditionRequest
    ):
        return _repo.set_rehab_condition(db, user_id, data)

    # ── Condition library ──────────────────────
    def list_conditions(self, db: Session):
        return _repo.list_conditions(db)

    # ── Plan CRUD ──────────────────────────────
    def list_my_plans(self, db: Session, user_id: uuid.UUID):
        return _repo.list_my_plans(db, user_id)

    def get_plan(self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID):
        return _repo.get_plan(db, plan_id, user_id)

    def create_plan(self, db: Session, user_id: uuid.UUID, data: RehabPlanCreate):
        return _repo.create_plan(db, user_id, data)

    def update_plan(
        self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID, data: RehabPlanUpdate
    ):
        return _repo.update_plan(db, plan_id, user_id, data)

    def delete_plan(self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID):
        return _repo.delete_plan(db, plan_id, user_id)

    # ── Routine CRUD ───────────────────────────
    def create_routine(
        self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID, data: RehabRoutineCreate
    ):
        return _repo.create_routine(db, plan_id, user_id, data)

    def update_routine(
        self, db: Session, routine_id: uuid.UUID, user_id: uuid.UUID, data: RehabRoutineUpdate
    ):
        return _repo.update_routine(db, routine_id, user_id, data)

    def delete_routine(self, db: Session, routine_id: uuid.UUID, user_id: uuid.UUID):
        return _repo.delete_routine(db, routine_id, user_id)

    # ── Routine Exercise CRUD ──────────────────
    def add_exercise_to_routine(
        self,
        db: Session,
        routine_id: uuid.UUID,
        user_id: uuid.UUID,
        data: RehabRoutineExerciseCreate,
    ):
        return _repo.add_exercise_to_routine(db, routine_id, user_id, data)

    def delete_routine_exercise(
        self, db: Session, entry_id: uuid.UUID, user_id: uuid.UUID
    ):
        return _repo.delete_routine_exercise(db, entry_id, user_id)
