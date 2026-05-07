import uuid
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from modules.meal_plans.models import MealPlan, MealPlanSlotMeal
from modules.meal_plans.schemas import (
    MealPlanCreate, MealPlanUpdate, MealPlanSlotCreate,
    MealPlanResponse, MealPlanListItem, MealPlanSlotResponse,
)


class MealPlanRepository:

    # ──────────────────────────────────────────
    # Guards
    # ──────────────────────────────────────────

    def _get_plan_or_404(self, db: Session, plan_id: uuid.UUID) -> MealPlan:
        plan = db.query(MealPlan).filter(MealPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Meal plan {plan_id} not found.")
        return plan

    def _require_owner(self, plan: MealPlan, user_id: uuid.UUID) -> None:
        if plan.created_by != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. You do not own this meal plan.")

    def _get_plan_owned(self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID) -> MealPlan:
        plan = self._get_plan_or_404(db, plan_id)
        self._require_owner(plan, user_id)
        return plan

    # ──────────────────────────────────────────
    # Read
    # ──────────────────────────────────────────

    def get_my_plans(self, db: Session, user_id: uuid.UUID) -> List[MealPlanListItem]:
        plans = (
            db.query(MealPlan)
            .filter(MealPlan.created_by == user_id, MealPlan.is_template.is_(False))
            .order_by(MealPlan.title)
            .all()
        )
        return [MealPlanListItem.from_orm_plan(p) for p in plans]

    def get_templates(self, db: Session) -> List[MealPlanListItem]:
        plans = (
            db.query(MealPlan)
            .filter(MealPlan.is_template.is_(True))
            .order_by(MealPlan.title)
            .all()
        )
        return [MealPlanListItem.from_orm_plan(p) for p in plans]

    def get_plan_by_id(self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID) -> MealPlanResponse:
        """Return a plan if user owns it OR it's a template (readable by all)."""
        plan = self._get_plan_or_404(db, plan_id)
        if not plan.is_template:
            self._require_owner(plan, user_id)
        return MealPlanResponse.from_orm_plan(plan)

    # ──────────────────────────────────────────
    # Create
    # ──────────────────────────────────────────

    def create_plan(
        self, db: Session, user_id: uuid.UUID, data: MealPlanCreate, is_admin: bool = False
    ) -> MealPlanResponse:
        plan = MealPlan(
            title=data.title,
            description=data.description,
            goal_type=data.goal_type,
            start_date=data.start_date,
            end_date=data.end_date,
            target_condition_id=data.target_condition_id,
            created_by=user_id,
            creator_role='admin' if is_admin else 'user',
            is_template=False,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return MealPlanResponse.from_orm_plan(plan)

    # ──────────────────────────────────────────
    # Update
    # ──────────────────────────────────────────

    def update_plan(
        self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID, data: MealPlanUpdate
    ) -> MealPlanResponse:
        plan = self._get_plan_owned(db, plan_id, user_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(plan, field, value)
        db.commit()
        db.refresh(plan)
        return MealPlanResponse.from_orm_plan(plan)

    # ──────────────────────────────────────────
    # Delete
    # ──────────────────────────────────────────

    def delete_plan(self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        plan = self._get_plan_owned(db, plan_id, user_id)
        title = plan.title
        db.delete(plan)
        db.commit()
        return {"message": f"Meal plan '{title}' deleted."}

    # ──────────────────────────────────────────
    # Slot management
    # ──────────────────────────────────────────

    def add_slot(
        self, db: Session, plan_id: uuid.UUID, user_id: uuid.UUID, data: MealPlanSlotCreate
    ) -> MealPlanSlotResponse:
        """Assign a meal to a slot. Enforces UNIQUE(plan, meal, meal_type)."""
        self._get_plan_owned(db, plan_id, user_id)

        slot = MealPlanSlotMeal(
            meal_plan_id=plan_id,
            meal_id=data.meal_id,
            meal_type=data.meal_type,
            note=data.note,
        )
        db.add(slot)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"This meal is already assigned to the '{data.meal_type}' slot in this plan.",
            )
        db.refresh(slot)
        return MealPlanSlotResponse.from_orm_slot(slot)

    def remove_slot(
        self, db: Session, plan_id: uuid.UUID, slot_id: uuid.UUID, user_id: uuid.UUID
    ) -> dict:
        """Remove a meal from a plan slot (owner only)."""
        self._get_plan_owned(db, plan_id, user_id)

        slot = (
            db.query(MealPlanSlotMeal)
            .filter(
                MealPlanSlotMeal.id == slot_id,
                MealPlanSlotMeal.meal_plan_id == plan_id,
            )
            .first()
        )
        if not slot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found in this meal plan.")

        db.delete(slot)
        db.commit()
        return {"message": "Meal removed from plan slot."}
