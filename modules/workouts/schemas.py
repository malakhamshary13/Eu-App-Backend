import uuid
from datetime import date
from typing import Optional, List
from pydantic import BaseModel

from db.database import ORMBaseModel


# ──────────────────────────────────────────
# Routine Exercise schemas
# ──────────────────────────────────────────

class RoutineExerciseCreate(BaseModel):
    """One exercise entry to add inside a routine."""
    exercise_id: uuid.UUID
    position: int = 0
    sets: Optional[int] = None
    reps: Optional[int] = None
    weight_kg: Optional[float] = None
    rest_time_seconds: Optional[int] = None


class RoutineExerciseResponse(ORMBaseModel):
    id: uuid.UUID
    exercise_id: uuid.UUID
    position: int
    sets: Optional[int] = None
    reps: Optional[int] = None
    weight_kg: Optional[float] = None
    rest_time_seconds: Optional[int] = None


# ──────────────────────────────────────────
# Routine schemas
# ──────────────────────────────────────────

class RoutineCreate(BaseModel):
    """Create a named group of exercises."""
    name: str
    description: Optional[str] = None
    exercises: List[RoutineExerciseCreate] = []


class RoutineUpdate(BaseModel):
    """Partial update of a routine."""
    name: Optional[str] = None
    description: Optional[str] = None
    exercises: Optional[List[RoutineExerciseCreate]] = None  # None = don't touch


class RoutineResponse(ORMBaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    is_template: bool = False
    exercises: List[RoutineExerciseResponse] = []


# ──────────────────────────────────────────
# Workout Plan Routine slot schemas
# ──────────────────────────────────────────

class PlanRoutineSlotCreate(BaseModel):
    """
    One scheduled slot in a plan.
    For 'nday' plans  → set day_number (1, 2, 3 …)
    For 'weekly' plans → set day_of_week (0=Sun … 6=Sat)
    Set is_rest_day=True to mark a rest day (no routine needed).
    """
    routine: Optional[RoutineCreate] = None      # inline routine creation
    routine_id: Optional[uuid.UUID] = None       # OR link an existing routine
    day_number: Optional[int] = None
    day_of_week: Optional[int] = None
    is_rest_day: bool = False
    position: int = 0


class PlanRoutineSlotResponse(ORMBaseModel):
    id: uuid.UUID
    routine_id: Optional[uuid.UUID] = None
    day_number: Optional[int] = None
    day_of_week: Optional[int] = None
    is_rest_day: bool = False
    position: int = 0
    routine: Optional[RoutineResponse] = None


# ──────────────────────────────────────────
# Workout Plan schemas
# ──────────────────────────────────────────

class WorkoutPlanCreate(BaseModel):
    """Payload for POST /workouts/plans."""
    title: str
    difficulty_level: Optional[str] = None    # 'beginner' | 'intermediate' | 'advanced'
    schedule_type: str = "nday"               # 'nday' | 'weekly'
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    slots: List[PlanRoutineSlotCreate] = []   # scheduled routine slots


class WorkoutPlanUpdate(BaseModel):
    """Partial update of a workout plan (owner only)."""
    title: Optional[str] = None
    difficulty_level: Optional[str] = None
    schedule_type: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class WorkoutPlanResponse(ORMBaseModel):
    """Full workout plan with nested routines and exercises."""
    id: uuid.UUID
    title: str
    difficulty_level: Optional[str] = None
    schedule_type: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_template: bool = False
    created_by: Optional[uuid.UUID] = None
    plan_routines: List[PlanRoutineSlotResponse] = []


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


# Re-export for backward compat with the existing router stub
WorkoutResponse = WorkoutPlanResponse
