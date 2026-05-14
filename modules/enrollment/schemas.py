import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, model_validator

from db.database import ORMBaseModel

# ─────────────────────────────────────────────────────────────────────────────
# Status rules
# ─────────────────────────────────────────────────────────────────────────────
EnrollmentStatus = Literal["active", "paused", "completed", "dropped"]

# Forward-only transitions enforced at the application layer
ENROLLMENT_TRANSITIONS: dict[str, set[str]] = {
    "active":    {"paused", "completed", "dropped"},
    "paused":    {"active", "dropped"},   # can resume or drop
    "completed": set(),                   # terminal
    "dropped":   set(),                   # terminal
}

# ─────────────────────────────────────────────────────────────────────────────
# Embedded plan summary (avoids a full plan join in list views)
# ─────────────────────────────────────────────────────────────────────────────
class WorkoutPlanSummary(ORMBaseModel):
    id: uuid.UUID
    title: str
    difficulty_level: Optional[str] = None
    schedule_type: Optional[str] = None
    description: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Enrollment schemas
# ─────────────────────────────────────────────────────────────────────────────
class EnrollmentCreate(BaseModel):
    """
    Enroll the authenticated user in a workout plan, a meal plan, or both.
    At least one of `workout_plan_id` / `meal_plan_id` must be supplied.
    """
    workout_plan_id: Optional[uuid.UUID] = None
    meal_plan_id:    Optional[uuid.UUID] = None

    @model_validator(mode="after")
    def at_least_one_plan(self) -> "EnrollmentCreate":
        if self.workout_plan_id is None and self.meal_plan_id is None:
            raise ValueError(
                "At least one of workout_plan_id or meal_plan_id must be provided."
            )
        return self


class EnrollmentStatusUpdate(BaseModel):
    """Advance or change the enrollment status."""
    status: EnrollmentStatus


class EnrollmentResponse(ORMBaseModel):
    id:              uuid.UUID
    user_id:         uuid.UUID
    workout_plan_id: Optional[uuid.UUID]  = None
    meal_plan_id:    Optional[uuid.UUID]  = None
    status:          str
    enrolled_at:     datetime
    workout_plan:    Optional[WorkoutPlanSummary] = None
