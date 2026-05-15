import uuid
from datetime import date
from typing import Optional, List, Literal
from pydantic import BaseModel, Field

from db.database import ORMBaseModel
from modules.meals.schemas import MealListItem


# ──────────────────────────────────────────
# Slot meal schemas
# ──────────────────────────────────────────

class MealPlanSlotCreate(BaseModel):
    """Assign a meal to a slot in the plan."""
    meal_id:   uuid.UUID
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"]
    note:      Optional[str] = None


class MealPlanSlotResponse(ORMBaseModel):
    id:        uuid.UUID
    meal_id:   uuid.UUID
    meal_type: str
    note:      Optional[str] = None
    meal:      Optional[MealListItem] = None   # embedded compact meal card

    @classmethod
    def from_orm_slot(cls, slot):
        return cls(
            id=slot.id,
            meal_id=slot.meal_id,
            meal_type=slot.meal_type,
            note=slot.note,
            meal=MealListItem.from_orm_meal(slot.meal) if slot.meal else None,
        )


# ──────────────────────────────────────────
# Condition summary (embedded in plan response)
# ──────────────────────────────────────────

class ConditionSummary(ORMBaseModel):
    id:           uuid.UUID
    code:         str
    display_name: str


# ──────────────────────────────────────────
# Meal Plan schemas
# ──────────────────────────────────────────

class MealPlanCreate(BaseModel):
    """POST /meal-plans/ — create a personal meal plan."""
    title:               str
    description:         Optional[str]       = None
    goal_type:           Optional[Literal[
        "weight_loss", "muscle_gain", "rehab", "general"
    ]] = None
    start_date:          Optional[date]      = None
    end_date:            Optional[date]      = Field(None, description="Must be >= start_date.")
    target_condition_id: Optional[uuid.UUID] = None


class MealPlanUpdate(BaseModel):
    """Partial update — only sent fields are changed."""
    title:               Optional[str]       = None
    description:         Optional[str]       = None
    goal_type:           Optional[str]       = None
    start_date:          Optional[date]      = None
    end_date:            Optional[date]      = None
    target_condition_id: Optional[uuid.UUID] = None


class MealPlanListItem(ORMBaseModel):
    """Compact card for list views."""
    id:          uuid.UUID
    title:       str
    description: Optional[str]  = None
    goal_type:   Optional[str]  = None
    start_date:  Optional[date] = None
    end_date:    Optional[date] = None
    is_template: bool = False
    slot_count:  int  = 0   # number of meals assigned
    target_condition: Optional[ConditionSummary] = None

    @classmethod
    def from_orm_plan(cls, plan):
        return cls(
            id=plan.id,
            title=plan.title,
            description=plan.description,
            goal_type=plan.goal_type,
            start_date=plan.start_date,
            end_date=plan.end_date,
            is_template=plan.is_template,
            slot_count=len(plan.slot_meals),
            target_condition=(
                ConditionSummary.model_validate(plan.target_condition)
                if plan.target_condition else None
            ),
        )


class MealPlanResponse(ORMBaseModel):
    """Full plan with all slot meals embedded."""
    id:          uuid.UUID
    title:       str
    description: Optional[str]  = None
    goal_type:   Optional[str]  = None
    start_date:  Optional[date] = None
    end_date:    Optional[date] = None
    is_template: bool = False
    created_by:  Optional[uuid.UUID] = None
    target_condition: Optional[ConditionSummary] = None
    slot_meals:  List[MealPlanSlotResponse] = []

    @classmethod
    def from_orm_plan(cls, plan):
        return cls(
            id=plan.id,
            title=plan.title,
            description=plan.description,
            goal_type=plan.goal_type,
            start_date=plan.start_date,
            end_date=plan.end_date,
            is_template=plan.is_template,
            created_by=plan.created_by,
            target_condition=(
                ConditionSummary.model_validate(plan.target_condition)
                if plan.target_condition else None
            ),
            slot_meals=[MealPlanSlotResponse.from_orm_slot(s) for s in plan.slot_meals],
        )
