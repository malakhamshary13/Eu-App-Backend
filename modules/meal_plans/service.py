import uuid
from typing import List
from sqlalchemy.orm import Session

from modules.meal_plans.repository import MealPlanRepository
from modules.meal_plans.schemas import MealPlanCreate, MealPlanUpdate, MealPlanSlotCreate

_repo = MealPlanRepository()


class MealPlanService:

    def get_my_plans(self, db: Session, user_id: uuid.UUID):
        return _repo.get_my_plans(db, user_id)

    def get_templates(self, db: Session):
        return _repo.get_templates(db)

    def get_plan(self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID):
        return _repo.get_plan_by_id(db, plan_id, user_id)

    def create_plan(self, db: Session, user_id: uuid.UUID, data: MealPlanCreate, is_admin: bool = False):
        return _repo.create_plan(db, user_id, data, is_admin=is_admin)

    def update_plan(self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID, data: MealPlanUpdate):
        return _repo.update_plan(db, plan_id, user_id, data)

    def delete_plan(self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID):
        return _repo.delete_plan(db, plan_id, user_id)

    def add_slot(self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID, data: MealPlanSlotCreate):
        return _repo.add_slot(db, plan_id, user_id, data)

    def remove_slot(self, db: Session, plan_id: uuid.UUID, slot_id: uuid.UUID, user_id: uuid.UUID):
        return _repo.remove_slot(db, plan_id, slot_id, user_id)
