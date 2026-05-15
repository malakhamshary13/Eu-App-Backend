import uuid
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel

from db.database import ORMBaseModel


# ──────────────────────────────────────────
# Nutrition
# ──────────────────────────────────────────

class NutritionResponse(ORMBaseModel):
    calories_cal:    Optional[int]   = None
    kilojoules_kj:   Optional[int]   = None
    protein_g:       Optional[float] = None
    total_fat_g:     Optional[float] = None
    carbohydrates_g: Optional[float] = None
    sugar_g:         Optional[float] = None
    saturated_fat_g: Optional[float] = None
    dietary_fibre_g: Optional[float] = None
    sodium_mg:       Optional[float] = None
    calcium_mg:      Optional[float] = None
    iron_mg:         Optional[float] = None


class NutritionCreate(BaseModel):
    calories_cal:    Optional[int]   = None
    kilojoules_kj:   Optional[int]   = None
    protein_g:       Optional[float] = None
    total_fat_g:     Optional[float] = None
    carbohydrates_g: Optional[float] = None
    sugar_g:         Optional[float] = None
    saturated_fat_g: Optional[float] = None
    dietary_fibre_g: Optional[float] = None
    sodium_mg:       Optional[float] = None
    calcium_mg:      Optional[float] = None
    iron_mg:         Optional[float] = None


# ──────────────────────────────────────────
# Meal list item (compact — for paginated list)
# ──────────────────────────────────────────

class MealListItem(ORMBaseModel):
    id:           uuid.UUID
    title:        str
    image_url:    Optional[str]   = None
    servings:     Optional[int]   = None
    prep_time:    Optional[str]   = None
    time_to_make: Optional[str]   = None
    nutrition:    Optional[NutritionResponse] = None
    tags:         List[str] = []   # flattened tag_name list

    # custom serialiser — tags is List[MealTag] ORM objects, flatten to strings
    @classmethod
    def from_orm_meal(cls, meal):
        return cls(
            id=meal.id,
            title=meal.title,
            image_url=meal.image_url,
            servings=meal.servings,
            prep_time=meal.prep_time,
            time_to_make=meal.time_to_make,
            nutrition=NutritionResponse.model_validate(meal.nutrition) if meal.nutrition else None,
            tags=[t.tag_name for t in meal.tags],
        )


# ──────────────────────────────────────────
# Meal detail (full)
# ──────────────────────────────────────────

class MealDetailResponse(ORMBaseModel):
    id:           uuid.UUID
    title:        str
    url:          Optional[str]   = None
    image_url:    Optional[str]   = None
    servings:     Optional[int]   = None
    prep_time:    Optional[str]   = None
    time_to_make: Optional[str]   = None
    instructions: Optional[Any]   = None   # JSONB — list of step strings
    guide_info:   Optional[str]   = None
    created_at:   Optional[datetime] = None
    nutrition:    Optional[NutritionResponse] = None
    tags:         List[str] = []
    ingredients:  List[str] = []   # flattened description list

    @classmethod
    def from_orm_meal(cls, meal):
        return cls(
            id=meal.id,
            title=meal.title,
            url=meal.url,
            image_url=meal.image_url,
            servings=meal.servings,
            prep_time=meal.prep_time,
            time_to_make=meal.time_to_make,
            instructions=meal.instructions,
            guide_info=meal.guide_info,
            created_at=meal.created_at,
            nutrition=NutritionResponse.model_validate(meal.nutrition) if meal.nutrition else None,
            tags=[t.tag_name for t in meal.tags],
            ingredients=[i.description for i in meal.ingredients],
        )


# ──────────────────────────────────────────
# Paginated response
# ──────────────────────────────────────────

class PaginatedMeals(BaseModel):
    total:     int
    page:      int
    page_size: int
    results:   List[MealListItem]


# ──────────────────────────────────────────
# Filter options
# ──────────────────────────────────────────

class MealFilterGroup(BaseModel):
    name: str
    tags: List[str]


class MealFilterOptions(BaseModel):
    groups: List[MealFilterGroup] = []


# ──────────────────────────────────────────
# Admin — Create / Update
# ──────────────────────────────────────────

class MealCreate(BaseModel):
    title:        str
    url:          Optional[str] = None
    image_url:    Optional[str] = None
    servings:     Optional[int] = None
    prep_time:    Optional[str] = None
    time_to_make: Optional[str] = None
    instructions: Optional[Any] = None
    guide_info:   Optional[str] = None
    nutrition:    Optional[NutritionCreate] = None
    tags:         List[str] = []
    ingredients:  List[str] = []


class MealUpdate(BaseModel):
    title:        Optional[str] = None
    url:          Optional[str] = None
    image_url:    Optional[str] = None
    servings:     Optional[int] = None
    prep_time:    Optional[str] = None
    time_to_make: Optional[str] = None
    instructions: Optional[Any] = None
    guide_info:   Optional[str] = None
    nutrition:    Optional[NutritionCreate] = None
    tags:         Optional[List[str]] = None        # None = don't touch
    ingredients:  Optional[List[str]] = None        # None = don't touch
