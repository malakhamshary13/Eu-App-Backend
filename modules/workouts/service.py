import uuid
from typing import List

from sqlalchemy.orm import Session

from modules.workouts.repository import WorkoutRepository
from modules.workouts.schemas import WorkoutPlanCreate, WorkoutPlanUpdate, PlanRoutineSlotCreate

_repo = WorkoutRepository()


class WorkoutService:

    def get_my_plans(self, db: Session, user_id: uuid.UUID):
        return _repo.get_my_plans(db, user_id)

    def get_plan(self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID):
        return _repo.get_plan_by_id(db, plan_id, user_id)

    def create_plan(self, db: Session, user_id: uuid.UUID, data: WorkoutPlanCreate):
        return _repo.create_plan(db, user_id, data)

    def update_plan(self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID, data: WorkoutPlanUpdate):
        return _repo.update_plan(db, plan_id, user_id, data)

    def delete_plan(self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID):
        return _repo.delete_plan(db, plan_id, user_id)

    def add_routine_slot(self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID, slot: PlanRoutineSlotCreate):
        return _repo.add_routine_slot(db, plan_id, user_id, slot)

    def remove_routine_slot(self, db: Session, plan_id: uuid.UUID, slot_id: uuid.UUID, user_id: uuid.UUID):
        return _repo.remove_routine_slot(db, plan_id, slot_id, user_id)
