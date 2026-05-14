import uuid
from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from db.database import ORMBaseModel


# ─────────────────────────────────────────────────────────────────────────────
# Allowed status values (mirrors the DB CHECK constraint)
# ─────────────────────────────────────────────────────────────────────────────
SessionStatus = Literal["scheduled", "in_progress", "completed", "abandoned", "skipped"]

# Valid forward-only transitions
VALID_TRANSITIONS: dict[str, set[str]] = {
    "scheduled":   {"in_progress", "skipped"},
    "in_progress": {"completed", "abandoned"},
    "completed":   set(),
    "abandoned":   set(),
    "skipped":     set(),
}


# ─────────────────────────────────────────────────────────────────────────────
# Embedded exercise detail (re-used from workouts module pattern)
# ─────────────────────────────────────────────────────────────────────────────
class ExerciseSummary(ORMBaseModel):
    id: uuid.UUID
    title: str
    exercise_type: Optional[str] = None
    muscle_group: Optional[str] = None
    equipment_category: Optional[str] = None
    thumbnail_url: Optional[str] = None
    hundred_percent_bodyweight: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Session Item schemas
# ─────────────────────────────────────────────────────────────────────────────
class SessionItemCreate(BaseModel):
    """Log ONE SET of ONE EXERCISE within a session."""
    exercise_id:    uuid.UUID
    set_number:     int    = Field(..., ge=1, description="Set number (1-based).")
    reps_completed: Optional[int]   = Field(None, ge=0, description="Reps performed (≥ 0).")
    weight_used:    Optional[float] = Field(None, ge=0.0, description="Weight in kg (≥ 0).")
    is_completed:   bool   = False


class SessionItemUpdate(BaseModel):
    """Correct a previously logged set (all fields optional)."""
    reps_completed: Optional[int]   = Field(None, ge=0)
    weight_used:    Optional[float] = Field(None, ge=0.0)
    is_completed:   Optional[bool]  = None


class SessionItemBulkCreate(BaseModel):
    """
    Log all sets of ONE exercise in a single request.
    The list must contain at least one item and sets must be in order.
    """
    exercise_id: uuid.UUID
    sets: List[SessionItemCreate] = Field(..., min_length=1)

    @model_validator(mode="after")
    def all_sets_for_same_exercise(self) -> "SessionItemBulkCreate":
        for s in self.sets:
            if s.exercise_id != self.exercise_id:
                raise ValueError(
                    "All sets in a bulk log must reference the same exercise_id."
                )
        return self


class SessionItemResponse(ORMBaseModel):
    id:             uuid.UUID
    session_id:     uuid.UUID
    exercise_id:    uuid.UUID
    set_number:     int
    reps_completed: Optional[int]   = None
    weight_used:    Optional[float] = None
    is_completed:   bool
    exercise:       Optional[ExerciseSummary] = None


# ─────────────────────────────────────────────────────────────────────────────
# Session schemas
# ─────────────────────────────────────────────────────────────────────────────
class SessionCreate(BaseModel):
    """
    Create a new workout session.

    - `workout_plan_id` + `routine_id` are optional but recommended so the
      session can be tied back to the plan for progress analysis.
    - `scheduled_date` defaults to today if omitted.
    - `status` defaults to 'scheduled'; pass 'in_progress' to start immediately.
    """
    workout_plan_id: Optional[uuid.UUID] = None
    routine_id:      Optional[uuid.UUID] = None
    scheduled_date:  Optional[date]      = None
    status: SessionStatus = "scheduled"


class SessionStatusUpdate(BaseModel):
    """Advance the session's status (forward-only transitions enforced)."""
    status: SessionStatus
    completed_at: Optional[datetime] = Field(
        None,
        description="Only required (and used) when transitioning to 'completed'.",
    )


class SessionResponse(ORMBaseModel):
    """Full session detail including all logged sets."""
    id:              uuid.UUID
    user_id:         uuid.UUID
    workout_plan_id: Optional[uuid.UUID] = None
    routine_id:      Optional[uuid.UUID] = None
    scheduled_date:  Optional[date]      = None
    started_at:      Optional[datetime]  = None
    completed_at:    Optional[datetime]  = None
    status:          str
    items:           List[SessionItemResponse] = []


class SessionListItem(ORMBaseModel):
    """Summary card used in list views (no nested items)."""
    id:              uuid.UUID
    workout_plan_id: Optional[uuid.UUID] = None
    routine_id:      Optional[uuid.UUID] = None
    scheduled_date:  Optional[date]      = None
    started_at:      Optional[datetime]  = None
    completed_at:    Optional[datetime]  = None
    status:          str


class SessionListResponse(BaseModel):
    total:   int
    results: List[SessionListItem]
