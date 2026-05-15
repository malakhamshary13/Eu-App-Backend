import uuid
from datetime import date
from typing import Optional, List, Literal
from pydantic import BaseModel, Field

from db.database import ORMBaseModel


# ──────────────────────────────────────────
# Exercise detail embedded in a routine
# ──────────────────────────────────────────

class ExerciseDetailInRoutine(ORMBaseModel):
    """Compact exercise card embedded inside a routine's exercise list."""
    id: uuid.UUID
    title: str
    exercise_type: Optional[str] = None
    muscle_group: Optional[str] = None
    equipment_category: Optional[str] = None
    thumbnail_url: Optional[str] = None
    url: Optional[str] = None
    media_type: Optional[str] = None
    hundred_percent_bodyweight: bool = False


# ──────────────────────────────────────────
# Routine Exercise schemas
# ──────────────────────────────────────────

class RoutineExerciseCreate(BaseModel):
    """Add a single exercise to a routine."""
    exercise_id:       uuid.UUID
    position:          int            = 0
    sets:              Optional[int]   = Field(None, ge=1, description="Sets (>= 1).")
    reps:              Optional[int]   = Field(None, ge=0, description="Reps per set (>= 0).")
    weight_kg:         Optional[float] = Field(None, ge=0.0, description="Weight in kg (>= 0).")
    rest_time_seconds: Optional[int]   = Field(None, ge=0, description="Rest in seconds (>= 0).")


class RoutineExerciseResponse(ORMBaseModel):
    id: uuid.UUID
    exercise_id: uuid.UUID
    position: int
    sets: Optional[int] = None
    reps: Optional[int] = None
    weight_kg: Optional[float] = None
    rest_time_seconds: Optional[int] = None
    exercise: Optional[ExerciseDetailInRoutine] = None   # full exercise details


# ──────────────────────────────────────────
# Workout Plan Routine (the routine itself)
# ──────────────────────────────────────────

class CreateRoutineInPlan(BaseModel):
    """
    POST /workouts/plans/{plan_id}/routines
    Creates a new routine slot directly on the plan.

    For 'nday' plans   → set day_number  (1, 2, 3 …)
    For 'weekly' plans → set day_of_week (0=Sun … 6=Sat)
    Set is_rest_day=True to mark a rest day (name is ignored).
    """
    name: str
    description: Optional[str] = None
    day_number: Optional[int] = None
    day_of_week: Optional[int] = None
    position: int = 0
    is_rest_day: bool = False


class WorkoutPlanRoutineResponse(ORMBaseModel):
    """A routine slot — returned nested inside a plan or as a standalone detail."""
    id: uuid.UUID
    name: Optional[str] = None
    description: Optional[str] = None
    day_number: Optional[int] = None
    day_of_week: Optional[int] = None
    is_rest_day: bool = False
    position: int = 0
    exercises: List[RoutineExerciseResponse] = []


# ──────────────────────────────────────────
# Workout Plan schemas
# ──────────────────────────────────────────

class WorkoutPlanCreate(BaseModel):
    """POST /workouts/plans — plan metadata only, no inline slots."""
    title:            str
    difficulty_level: Optional[Literal["beginner", "intermediate", "advanced"]] = None
    schedule_type:    Literal["nday", "weekly"] = "nday"
    description:      Optional[str]  = None
    start_date:       Optional[date] = None
    end_date:         Optional[date] = None


class WorkoutPlanUpdate(BaseModel):
    """Partial update of a workout plan (owner only)."""
    title:            Optional[str]   = None
    difficulty_level: Optional[Literal["beginner", "intermediate", "advanced"]] = None
    schedule_type:    Optional[Literal["nday", "weekly"]] = None
    description:      Optional[str]  = None
    start_date:       Optional[date] = None
    end_date:         Optional[date] = None


class WorkoutPlanResponse(ORMBaseModel):
    """Full workout plan with nested routines and their exercises."""
    id: uuid.UUID
    title: str
    difficulty_level: Optional[str] = None
    schedule_type: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_template: bool = False
    created_by: Optional[uuid.UUID] = None
    plan_routines: List[WorkoutPlanRoutineResponse] = []


class WorkoutPlanListItem(ORMBaseModel):
    """Summary card for list views (no nested data)."""
    id: uuid.UUID
    title: str
    difficulty_level: Optional[str] = None
    schedule_type: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_template: bool = False


# Alias kept for any existing references
WorkoutResponse = WorkoutPlanResponse
