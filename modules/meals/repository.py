import uuid
import operator as op
from typing import Optional, List

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from modules.meals.models import (
    Meal, MealNutrition, MealTag, Ingredient,
    Condition, ConditionNutritionRule, ConditionFoodFilter, UserChronicCondition,
)
from modules.meals.schemas import (
    MealCreate, MealUpdate, MealListItem, MealDetailResponse,
    PaginatedMeals, MealFilterOptions, NutritionCreate,
)
from modules.users.models import HealthProfile


# ──────────────────────────────────────────
# Goal → nutrition threshold defaults
# Applied when use_profile=True and user has no linked conditions.
# ──────────────────────────────────────────

_GOAL_NUTRITION_DEFAULTS = {
    "weight_loss": {
        "max_calories_cal":   450,
        "min_protein_g":      15.0,
        "max_total_fat_g":    18.0,
        "max_sugar_g":        12.0,
    },
    "muscle_gain": {
        "min_protein_g":      25.0,
        "min_calories_cal":   350,
        "max_total_fat_g":    25.0,
    },
    "rehab": {
        "max_sodium_mg":      600.0,
        "max_total_fat_g":    20.0,
    },
    "maintenance": {},   # no filters — full library
}

# Maps condition_nutrition_rules.metric to MealNutrition column attr
_METRIC_MAP = {
    "calories_cal":     "calories_cal",
    "protein_g":        "protein_g",
    "total_fat_g":      "total_fat_g",
    "carbohydrates_g":  "carbohydrates_g",
    "sugar_g":          "sugar_g",
    "saturated_fat_g":  "saturated_fat_g",
    "dietary_fibre_g":  "dietary_fibre_g",
    "sodium_mg":        "sodium_mg",
    "calcium_mg":       "calcium_mg",
    "iron_mg":          "iron_mg",
}

_OPS = {"<": op.lt, "<=": op.le, ">": op.gt, ">=": op.ge}

_FILTER_GROUPS = [
    (
        "Meals",
        [
            "Breakfast", "lunch", "Mains", "One-dish Meals", "Side Dishes",
            "Salads", "Soups", "Snacks and Light Meals", "Starters, dips",
            "Desserts", "Drinks", "Dressings", "Sauces", "Pies, tarts and flans",
            "Roasts", "Frittatas, quiches", "Fritters", "Casseroles, Stews",
            "Curries, Asian-style", "Pasta, rice and noodle dishes", "Stir-fries",
            "Preserves",
        ],
    ),
    (
        "Special Diets",
        [
            "Dairy free", "Diabetes-friendly", "Gluten free", "Gluten-free option",
            "Low FODMAP recipe options for IBS", "Low FODMAP recipes for IBS",
            "Nut free", "Vegan", "Vegan option", "Vegetarian",
        ],
    ),
    (
        "Nutrition",
        [
            "0.5 vege serve", "1 vege serve", "1.5 vege serves", "2 vege serves",
            "2.5 vege serves", "3 vege serves", "3.5 vege serves", "4 vege serves",
            "4.5 vege serves", "5 vege serves", "5.5 vege serves", "6 vege serves",
            "6.5 vege serves", "7 vege serves", "8 vege serves", "High calcium",
            "High fibre", "High iron", "High protein", "high-protein", "Low fat",
            "Low kilojoule", "Low sodium", "Lower carb",
        ],
    ),
    (
        "Collections",
        [
            "$AVER (low cost)", "5pm panic!", "Family favourites", "Freezes well",
            "Homemade Takeaways", "How to cook", "How to cook the basics",
            "Kids can cook", "Kids in the kitchen", "Made just for two",
            "Makeovers", "Meals for one", "Reader recipes", "RECIPE",
            "School lunches", "Sponsor recipes", "Work lunches",
        ],
    ),
    (
        "Cooking",
        [
            "Baking", "Barbecue", "Marinades, rubs", "Microwave",
            "No, or minimal, cooking", "Ready in 20 minutes", "Slow cooker",
        ],
    ),
    ("Seasons", ["Christmas"]),
]


class MealRepository:

    # ──────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────

    def _get_meal_or_404(self, db: Session, meal_id: uuid.UUID) -> Meal:
        meal = db.query(Meal).filter(Meal.id == meal_id).first()
        if not meal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Meal {meal_id} not found.")
        return meal

    def _apply_nutrition_filter(self, q, col_name: str, comparator: str, value: float):
        """Apply a single nutrition threshold filter via JOIN on MealNutrition."""
        col = getattr(MealNutrition, col_name, None)
        if col is None:
            return q
        op_fn = _OPS.get(comparator)
        if op_fn is None:
            return q
        return q.filter(op_fn(col, value))

    # ──────────────────────────────────────────
    # Filter options
    # ──────────────────────────────────────────

    def get_filter_options(self, db: Session) -> MealFilterOptions:
        rows = (
            db.query(MealTag.tag_name)
            .distinct()
            .order_by(MealTag.tag_name)
            .all()
        )
        tags = [r[0] for r in rows if r[0] and r[0].strip()]
        available_tags = set(tags)
        groups = []
        grouped_tags = set()

        for group_name, group_tags in _FILTER_GROUPS:
            present_group_tags = [tag for tag in group_tags if tag in available_tags]
            if present_group_tags:
                groups.append({"name": group_name, "tags": present_group_tags})
                grouped_tags.update(present_group_tags)

        other_tags = [tag for tag in tags if tag not in grouped_tags]
        if other_tags:
            groups.append({"name": "More", "tags": other_tags})

        return MealFilterOptions(groups=groups)

    # ──────────────────────────────────────────
    # List (paginated + filtered)
    # ──────────────────────────────────────────

    def get_meals(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        tag: Optional[str] = None,
        tags: Optional[List[str]] = None,
        max_calories: Optional[int] = None,
        min_protein_g: Optional[float] = None,
        max_fat_g: Optional[float] = None,
        max_sodium_mg: Optional[float] = None,
        max_sugar_g: Optional[float] = None,
        use_profile: bool = False,
        user_id: Optional[uuid.UUID] = None,
    ) -> PaginatedMeals:

        q = db.query(Meal).join(MealNutrition, isouter=True)

        # ── Search ──
        if search:
            q = q.filter(Meal.title.ilike(f"%{search}%"))

        selected_tags = []
        if tag:
            selected_tags.append(tag)
        if tags:
            selected_tags.extend(tags)

        normalized_tags = sorted({
            tag_part.strip().lower()
            for value in selected_tags
            for tag_part in value.split(",")
            if tag_part.strip()
        })

        # ── Tag filter ──
        if normalized_tags:
            matching_meal_ids = (
                db.query(MealTag.meal_id)
                .filter(func.lower(MealTag.tag_name).in_(normalized_tags))
                .group_by(MealTag.meal_id)
                .having(func.count(func.distinct(func.lower(MealTag.tag_name))) == len(normalized_tags))
                .scalar_subquery()
            )
            q = q.filter(Meal.id.in_(matching_meal_ids))

        # ── Explicit nutrition filters ──
        if max_calories is not None:
            q = q.filter(MealNutrition.calories_cal <= max_calories)
        if min_protein_g is not None:
            q = q.filter(MealNutrition.protein_g >= min_protein_g)
        if max_fat_g is not None:
            q = q.filter(MealNutrition.total_fat_g <= max_fat_g)
        if max_sodium_mg is not None:
            q = q.filter(MealNutrition.sodium_mg <= max_sodium_mg)
        if max_sugar_g is not None:
            q = q.filter(MealNutrition.sugar_g <= max_sugar_g)

        # ── Profile-based goal defaults ──
        if use_profile and user_id:
            profile = db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()
            if profile and profile.primary_goal:
                defaults = _GOAL_NUTRITION_DEFAULTS.get(profile.primary_goal, {})
                if "max_calories_cal" in defaults and max_calories is None:
                    q = q.filter(MealNutrition.calories_cal <= defaults["max_calories_cal"])
                if "min_calories_cal" in defaults:
                    q = q.filter(MealNutrition.calories_cal >= defaults["min_calories_cal"])
                if "min_protein_g" in defaults and min_protein_g is None:
                    q = q.filter(MealNutrition.protein_g >= defaults["min_protein_g"])
                if "max_total_fat_g" in defaults and max_fat_g is None:
                    q = q.filter(MealNutrition.total_fat_g <= defaults["max_total_fat_g"])
                if "max_sugar_g" in defaults and max_sugar_g is None:
                    q = q.filter(MealNutrition.sugar_g <= defaults["max_sugar_g"])
                if "max_sodium_mg" in defaults and max_sodium_mg is None:
                    q = q.filter(MealNutrition.sodium_mg <= defaults["max_sodium_mg"])

        total = q.count()
        meals = q.offset((page - 1) * page_size).limit(page_size).all()
        return PaginatedMeals(
            total=total, page=page, page_size=page_size,
            results=[MealListItem.from_orm_meal(m) for m in meals],
        )

    # ──────────────────────────────────────────
    # Detail
    # ──────────────────────────────────────────

    def get_meal_by_id(self, db: Session, meal_id: uuid.UUID) -> MealDetailResponse:
        meal = self._get_meal_or_404(db, meal_id)
        return MealDetailResponse.from_orm_meal(meal)

    # ──────────────────────────────────────────
    # Recommend (condition-aware)
    # ──────────────────────────────────────────

    def recommend_meals(
        self,
        db: Session,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedMeals:
        """
        Return meals filtered by the user's chronic conditions + health goal.

        Steps:
        1. Load health profile (primary_goal, weight_kg)
        2. Load linked conditions → food_filters + nutrition_rules
        3. Exclude meals with forbidden ingredients/tags
        4. Require meals with required labels (tags)
        5. Apply per-serving nutrition thresholds
        6. Fall back to goal defaults if no conditions linked
        """
        profile = db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()

        # Gather user's linked conditions
        chronic = (
            db.query(UserChronicCondition)
            .filter(
                UserChronicCondition.user_id == user_id,
                UserChronicCondition.condition_id.isnot(None),
            )
            .all()
        )
        condition_ids = [c.condition_id for c in chronic]

        q = db.query(Meal).join(MealNutrition, isouter=True)

        if condition_ids:
            # ── Collect all food filters for user's conditions ──
            food_filters = (
                db.query(ConditionFoodFilter)
                .filter(ConditionFoodFilter.condition_id.in_(condition_ids))
                .all()
            )

            for ff in food_filters:
                token = ff.token.lower()
                if ff.filter_type == "exclude_ingredient":
                    # Exclude meals that have an ingredient matching this token
                    q = q.filter(
                        ~Meal.id.in_(
                            db.query(Ingredient.meal_id)
                            .filter(Ingredient.description.ilike(f"%{token}%"))
                            .scalar_subquery()
                        )
                    )
                elif ff.filter_type == "exclude_tag":
                    q = q.filter(
                        ~Meal.id.in_(
                            db.query(MealTag.meal_id)
                            .filter(MealTag.tag_name.ilike(token))
                            .scalar_subquery()
                        )
                    )
                elif ff.filter_type == "require_label":
                    q = q.filter(
                        Meal.id.in_(
                            db.query(MealTag.meal_id)
                            .filter(MealTag.tag_name.ilike(token))
                            .scalar_subquery()
                        )
                    )

            # ── Apply nutrition rules (per_serving scope) ──
            nutrition_rules = (
                db.query(ConditionNutritionRule)
                .filter(
                    ConditionNutritionRule.condition_id.in_(condition_ids),
                    ConditionNutritionRule.scope == "per_serving",
                    ConditionNutritionRule.priority == "default",
                )
                .all()
            )

            weight_kg = float(profile.weight) if profile and profile.weight else 70.0

            for rule in nutrition_rules:
                metric = _METRIC_MAP.get(rule.metric)
                if metric:
                    threshold = float(rule.value)
                    q = self._apply_nutrition_filter(q, metric, rule.operator, threshold)

        else:
            # ── No conditions → fall back to goal defaults ──
            if profile and profile.primary_goal:
                defaults = _GOAL_NUTRITION_DEFAULTS.get(profile.primary_goal, {})
                if "max_calories_cal" in defaults:
                    q = q.filter(MealNutrition.calories_cal <= defaults["max_calories_cal"])
                if "min_calories_cal" in defaults:
                    q = q.filter(MealNutrition.calories_cal >= defaults["min_calories_cal"])
                if "min_protein_g" in defaults:
                    q = q.filter(MealNutrition.protein_g >= defaults["min_protein_g"])
                if "max_total_fat_g" in defaults:
                    q = q.filter(MealNutrition.total_fat_g <= defaults["max_total_fat_g"])
                if "max_sodium_mg" in defaults:
                    q = q.filter(MealNutrition.sodium_mg <= defaults["max_sodium_mg"])

        total = q.count()
        meals = q.offset((page - 1) * page_size).limit(page_size).all()
        return PaginatedMeals(
            total=total, page=page, page_size=page_size,
            results=[MealListItem.from_orm_meal(m) for m in meals],
        )

    # ──────────────────────────────────────────
    # Admin — Create
    # ──────────────────────────────────────────

    def create_meal(self, db: Session, data: MealCreate) -> MealDetailResponse:
        meal = Meal(
            title=data.title, url=data.url, image_url=data.image_url,
            servings=data.servings, prep_time=data.prep_time,
            time_to_make=data.time_to_make, instructions=data.instructions,
            guide_info=data.guide_info,
        )
        db.add(meal)
        db.flush()

        if data.nutrition:
            db.add(MealNutrition(meal_id=meal.id, **data.nutrition.model_dump()))

        for tag in data.tags:
            db.add(MealTag(meal_id=meal.id, tag_name=tag))

        for desc in data.ingredients:
            db.add(Ingredient(meal_id=meal.id, description=desc))

        db.commit()
        db.refresh(meal)
        return MealDetailResponse.from_orm_meal(meal)

    # ──────────────────────────────────────────
    # Admin — Delete
    # ──────────────────────────────────────────

    def delete_meal(self, db: Session, meal_id: uuid.UUID) -> dict:
        meal = self._get_meal_or_404(db, meal_id)
        title = meal.title
        db.delete(meal)
        db.commit()
        return {"message": f"Meal '{title}' deleted."}
