from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class NutritionStatsResponse(BaseModel):
    """
    Output of public.get_user_nutrition_stats(u_id, start_date, end_date).

    The procedure sums nutrients from tracker.user_meal_schedule joined with
    library.meal_nutrition for all **eaten** meals where
    start_date <= scheduled_date <= end_date (both inclusive).

    Fields are `None` when the caller requests a single specific nutrient
    and that field is outside the requested scope.
    """

    start_date: date = Field(..., description="Start of the tracking window (inclusive).")
    end_date:   date = Field(..., description="End of the tracking window (inclusive).")
    nutrient_filter: str = Field(
        ...,
        description="Which nutrient was requested ('all' returns every column).",
    )

    # All nutrient columns are optional so we can mask them when a single
    # nutrient is requested — the DB still calculates everything; we just
    # don't expose irrelevant columns.
    total_protein:  Optional[float] = Field(None, description="Total protein consumed in grams (g) over the window.")
    total_calories: Optional[int]   = Field(None, description="Total calories consumed (kcal) over the window.")
    total_carbs:    Optional[float] = Field(None, description="Total carbohydrates consumed in grams (g) over the window.")
    total_fat:      Optional[float] = Field(None, description="Total fat consumed in grams (g) over the window.")
    total_sodium:   Optional[float] = Field(None, description="Total sodium consumed in milligrams (mg) over the window.")
