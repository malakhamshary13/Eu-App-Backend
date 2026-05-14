import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.auth import get_current_user
from core.limiter import limiter
from db.database import get_db
from modules.meal_tracking.nutrition_schemas import NutritionStatsResponse

router = APIRouter(prefix="/nutrition", tags=["Nutrition Tracking"])

# ── Allowed nutrient fields ────────────────────────────────────────────────────
VALID_NUTRIENTS = {"protein", "calories", "carbs", "fat", "sodium", "all"}


@router.get(
    "/stats",
    response_model=NutritionStatsResponse,
    summary="Get nutrient totals for the authenticated user",
)
@limiter.limit("30/minute")
def get_nutrition_stats(
    request: Request,
    start_date: date = Query(
        ...,
        description="Start of the date window (inclusive). Format: YYYY-MM-DD.",
    ),
    end_date: date = Query(
        ...,
        description="End of the date window (inclusive). Format: YYYY-MM-DD.",
    ),
    nutrient: str = Query(
        "all",
        description=(
            "Which nutrient to return. One of: "
            "'protein', 'calories', 'carbs', 'fat', 'sodium', 'all'."
        ),
    ),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Calls **`public.get_user_nutrition_stats(u_id, start_date, end_date)`**
    which sums nutrients from `tracker.user_meal_schedule` joined with
    `library.meal_nutrition` for all **eaten** meals where
    `start_date ≤ scheduled_date ≤ end_date` (both inclusive).

    ### Date range examples
    | Goal | start_date | end_date |
    |---|---|---|
    | Today only | today | today |
    | This week | Monday's date | today |
    | Last 30 days | today − 29 days | today |

    ### `nutrient` filter
    Pass a specific nutrient name to get a lean response, or `"all"` to get
    every column. The DB procedure always aggregates all five columns; the
    `nutrient` param only controls what is included in the response payload.
    """
    # Validate nutrient param
    if nutrient not in VALID_NUTRIENTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid nutrient '{nutrient}'. "
                f"Must be one of: {', '.join(sorted(VALID_NUTRIENTS))}."
            ),
        )

    # Validate date range
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must be on or after start_date.",
        )

    user_id = uuid.UUID(str(current_user.id))

    # Call the stored procedure — always returns exactly one row (COALESCE ensures non-null)
    result = db.execute(
        text(
            "SELECT total_protein, total_calories, total_carbs, "
            "       total_fat, total_sodium "
            "FROM public.get_user_nutrition_stats(:u_id, :start_date, :end_date)"
        ),
        {
            "u_id":       str(user_id),
            "start_date": start_date,
            "end_date":   end_date,
        },
    ).fetchone()

    if result is None:
        # Should never happen (COALESCE in procedure), but be safe
        row = {
            "total_protein":  0,
            "total_calories": 0,
            "total_carbs":    0,
            "total_fat":      0,
            "total_sodium":   0,
        }
    else:
        row = result._mapping  # type: ignore[attr-defined]

    # Build response; mask unused fields when a specific nutrient is requested
    def _keep(field: str) -> bool:
        return nutrient == "all" or nutrient == field

    return NutritionStatsResponse(
        start_date=start_date,
        end_date=end_date,
        nutrient_filter=nutrient,
        total_protein=float(row["total_protein"])   if _keep("protein")  else None,
        total_calories=int(row["total_calories"])    if _keep("calories") else None,
        total_carbs=float(row["total_carbs"])        if _keep("carbs")    else None,
        total_fat=float(row["total_fat"])            if _keep("fat")      else None,
        total_sodium=float(row["total_sodium"])      if _keep("sodium")   else None,
    )
