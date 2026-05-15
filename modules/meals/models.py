from sqlalchemy import Column, String, Boolean, Integer, Text, Numeric, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text
import uuid

from db.database import Base


class Meal(Base):
    """Maps to library.meals."""
    __tablename__ = "meals"
    __table_args__ = {'schema': 'library'}

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title        = Column(String, nullable=False, unique=True)
    url          = Column(Text, nullable=True)
    image_url    = Column(Text, nullable=True)
    servings     = Column(Integer, nullable=True)
    prep_time    = Column(String, nullable=True)
    time_to_make = Column(String, nullable=True)
    instructions = Column(JSON, nullable=True)   # JSONB array of step strings
    guide_info   = Column(Text, nullable=True)
    created_at   = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))

    nutrition   = relationship("MealNutrition", back_populates="meal", uselist=False, lazy="selectin")
    tags        = relationship("MealTag",       back_populates="meal", cascade="all, delete-orphan", lazy="selectin")
    ingredients = relationship("Ingredient",    back_populates="meal", cascade="all, delete-orphan", lazy="selectin")


class MealNutrition(Base):
    """Maps to library.meal_nutrition. 1:1 with Meal."""
    __tablename__ = "meal_nutrition"
    __table_args__ = {'schema': 'library'}

    meal_id          = Column(UUID(as_uuid=True), ForeignKey("library.meals.id", ondelete="CASCADE"), primary_key=True)
    calories_cal     = Column(Integer,      nullable=True)
    kilojoules_kj    = Column(Integer,      nullable=True)
    protein_g        = Column(Numeric(6,2), nullable=True)
    total_fat_g      = Column(Numeric(6,2), nullable=True)
    carbohydrates_g  = Column(Numeric(6,2), nullable=True)
    sugar_g          = Column(Numeric(6,2), nullable=True)
    saturated_fat_g  = Column(Numeric(6,2), nullable=True)
    dietary_fibre_g  = Column(Numeric(6,2), nullable=True)
    sodium_mg        = Column(Numeric(6,2), nullable=True)
    calcium_mg       = Column(Numeric(6,2), nullable=True)
    iron_mg          = Column(Numeric(6,2), nullable=True)

    meal = relationship("Meal", back_populates="nutrition")


class MealTag(Base):
    """Maps to library.meal_tags."""
    __tablename__ = "meal_tags"
    __table_args__ = {'schema': 'library'}

    id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meal_id  = Column(UUID(as_uuid=True), ForeignKey("library.meals.id", ondelete="CASCADE"), nullable=False)
    tag_name = Column(String, nullable=False)

    meal = relationship("Meal", back_populates="tags")


class Ingredient(Base):
    """Maps to library.ingredients."""
    __tablename__ = "ingredients"
    __table_args__ = {'schema': 'library'}

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meal_id     = Column(UUID(as_uuid=True), ForeignKey("library.meals.id", ondelete="CASCADE"), nullable=False)
    description = Column(Text, nullable=False)

    meal = relationship("Meal", back_populates="ingredients")


class Condition(Base):
    """Maps to library.conditions."""
    __tablename__ = "conditions"
    __table_args__ = {'schema': 'library'}

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code         = Column(String, nullable=False, unique=True)
    display_name = Column(String, nullable=False)
    description  = Column(Text, nullable=True)
    is_active    = Column(Boolean, nullable=False, default=True)

    nutrition_rules = relationship("ConditionNutritionRule", back_populates="condition", lazy="selectin")
    food_filters    = relationship("ConditionFoodFilter",    back_populates="condition", lazy="selectin")


class ConditionNutritionRule(Base):
    """Maps to library.condition_nutrition_rules."""
    __tablename__ = "condition_nutrition_rules"
    __table_args__ = {'schema': 'library'}

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    condition_id = Column(UUID(as_uuid=True), ForeignKey("library.conditions.id"), nullable=False)
    metric       = Column(String, nullable=False)   # e.g. 'sodium_mg', 'protein_g'
    operator     = Column(String, nullable=False)   # '<' | '<=' | '>' | '>='
    value        = Column(Numeric, nullable=False)
    priority     = Column(String, nullable=False, default='default')
    scope        = Column(String, nullable=False, default='per_day')
    note         = Column(Text, nullable=True)

    condition = relationship("Condition", back_populates="nutrition_rules")


class ConditionFoodFilter(Base):
    """Maps to library.condition_food_filters."""
    __tablename__ = "condition_food_filters"
    __table_args__ = {'schema': 'library'}

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    condition_id = Column(UUID(as_uuid=True), ForeignKey("library.conditions.id"), nullable=False)
    filter_type  = Column(String, nullable=False)  # 'exclude_ingredient'|'exclude_tag'|'require_label'
    token        = Column(String, nullable=False)
    note         = Column(Text, nullable=True)

    condition = relationship("Condition", back_populates="food_filters")


class UserChronicCondition(Base):
    """Maps to profile.user_chronic_conditions."""
    __tablename__ = "user_chronic_conditions"
    __table_args__ = {'schema': 'profile'}

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id        = Column(UUID(as_uuid=True), nullable=False)
    condition_name = Column(String, nullable=False)
    condition_id   = Column(UUID(as_uuid=True), ForeignKey("library.conditions.id", ondelete="SET NULL"), nullable=True)

    condition = relationship("Condition", lazy="selectin")
