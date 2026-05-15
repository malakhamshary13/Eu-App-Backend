import uuid
from typing import List

from sqlalchemy.orm import Session

from modules.workouts.repository import WorkoutRepository
from modules.workouts.schemas import (
    WorkoutPlanCreate, WorkoutPlanUpdate,
    CreateRoutineInPlan, RoutineExerciseCreate,
)

_repo = WorkoutRepository()


class WorkoutService:

    def get_my_plans(self, db: Session, user_id: uuid.UUID):
        return _repo.get_my_plans(db, user_id)

    def get_plan(self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID):
        return _repo.get_plan_by_id(db, plan_id, user_id)

    def get_routine(self, db: Session, routine_id: uuid.UUID, user_id: uuid.UUID):
        return _repo.get_routine_by_id(db, routine_id, user_id)

    def create_plan(self, db: Session, user_id: uuid.UUID, data: WorkoutPlanCreate):
        return _repo.create_plan(db, user_id, data)

    def create_routine_for_plan(
        self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID, data: CreateRoutineInPlan
    ):
        return _repo.create_routine_for_plan(db, plan_id, user_id, data)

    def add_exercise_to_routine(
        self, db: Session, routine_id: uuid.UUID, user_id: uuid.UUID, data: RoutineExerciseCreate
    ):
        return _repo.add_exercise_to_routine(db, routine_id, user_id, data)

    def update_plan(self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID, data: WorkoutPlanUpdate):
        return _repo.update_plan(db, plan_id, user_id, data)

    def delete_plan(self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID):
        return _repo.delete_plan(db, plan_id, user_id)

    def delete_routine(self, db: Session, routine_id: uuid.UUID, user_id: uuid.UUID):
        return _repo.delete_routine(db, routine_id, user_id)
