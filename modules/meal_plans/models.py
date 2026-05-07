from sqlalchemy import Column, String, Boolean, Date, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from db.database import Base


class MealPlan(Base):
    """
    Maps to plans.meal_plans.
    Can be an admin template (is_template=True) or a personal user plan.
    Optionally targets a specific medical condition via target_condition_id.
    """
    __tablename__ = "meal_plans"
    __table_args__ = {'schema': 'plans'}

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title                = Column(String, nullable=False)
    description          = Column(Text, nullable=True)
    goal_type            = Column(String, nullable=True)   # e.g. 'weight_loss', 'muscle_gain'
    start_date           = Column(Date, nullable=True)
    end_date             = Column(Date, nullable=True)
    target_condition_id  = Column(
        UUID(as_uuid=True),
        ForeignKey("library.conditions.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by    = Column(UUID(as_uuid=True), nullable=True)   # FK to auth.users.id
    creator_role  = Column(String, nullable=True, default='user')  # 'admin' | 'user'
    is_template   = Column(Boolean, nullable=False, default=False)

    slot_meals = relationship(
        "MealPlanSlotMeal",
        back_populates="meal_plan",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    target_condition = relationship("Condition", lazy="selectin", foreign_keys=[target_condition_id])


class MealPlanSlotMeal(Base):
    """
    Maps to plans.meal_plan_slot_meals.
    Assigns a specific meal to a meal-type slot (breakfast/lunch/dinner/snack) within a plan.
    UNIQUE on (meal_plan_id, meal_id, meal_type).
    """
    __tablename__ = "meal_plan_slot_meals"
    __table_args__ = (
        UniqueConstraint("meal_plan_id", "meal_id", "meal_type", name="uq_plan_meal_type"),
        {'schema': 'plans'},
    )

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meal_plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("plans.meal_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    meal_id      = Column(
        UUID(as_uuid=True),
        ForeignKey("library.meals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    meal_type    = Column(String, nullable=False)   # 'breakfast'|'lunch'|'dinner'|'snack'
    note         = Column(Text, nullable=True)

    meal_plan = relationship("MealPlan", back_populates="slot_meals")
    meal      = relationship("Meal", lazy="selectin")
