import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel
from db.database import ORMBaseModel


# ──────────────────────────────────────────
# Rehab Exercise (library item)
# ──────────────────────────────────────────

class RehabExerciseOut(ORMBaseModel):
    """Compact rehab exercise card returned in lists."""
    id:               uuid.UUID
    slug:             str
    title:            str
    media_type:       Optional[str] = None
    youtube_id:       Optional[str] = None
    youtube_url:      Optional[str] = None
    thumbnail_url:    Optional[str] = None
    image_url:        Optional[str] = None
    description:      Optional[str] = None
    muscles_involved: Optional[List[str]] = []
    categories:       Optional[List[str]] = []
    tags:             Optional[List[str]] = []


# ──────────────────────────────────────────
# Rehab Condition (library item)
# ──────────────────────────────────────────

class RehabConditionOut(ORMBaseModel):
    id:          uuid.UUID
    slug:        str
    name:        str
    description: Optional[str] = None
    image_url:   Optional[str] = None


# ──────────────────────────────────────────
# User Rehab Condition — PUT endpoint
# ──────────────────────────────────────────

class SetRehabConditionRequest(BaseModel):
    """
    PUT /rehab/my-condition
    Set (or clear) the active rehab condition for the current user.
    Passing null/None clears the condition.
    """
    condition_id: Optional[uuid.UUID] = None
    injury_details:   Optional[str] = None
    recovery_stage:   Optional[str] = None


class UserRehabConditionOut(ORMBaseModel):
    """What we return after updating the user's rehab condition."""
    user_id:        uuid.UUID
    condition_id:   Optional[uuid.UUID] = None
    injury_details: Optional[str] = None
    recovery_stage: Optional[str] = None
    updated_at:     Optional[datetime] = None


# ──────────────────────────────────────────
# Rehab Routine Exercise schemas
# ──────────────────────────────────────────

class RehabRoutineExerciseCreate(BaseModel):
    """Add an exercise to a routine with prescription data."""
    exercise_id:       uuid.UUID
    sets:              Optional[int] = None
    reps:              Optional[int] = None
    hold_time_seconds: Optional[int] = None
    rest_seconds:      Optional[int] = None
    notes:             Optional[str] = None
    order_index:       int = 0


class RehabRoutineExerciseOut(ORMBaseModel):
    id:                uuid.UUID
    exercise_id:       Optional[uuid.UUID] = None
    sets:              Optional[int] = None
    reps:              Optional[int] = None
    hold_time_seconds: Optional[int] = None
    rest_seconds:      Optional[int] = None
    notes:             Optional[str] = None
    order_index:       int = 0
    exercise:          Optional[RehabExerciseOut] = None


# ──────────────────────────────────────────
# Rehab Routine schemas
# ──────────────────────────────────────────

class RehabRoutineCreate(BaseModel):
    name:        str
    order_index: int = 0


class RehabRoutineUpdate(BaseModel):
    name:        Optional[str] = None
    order_index: Optional[int] = None


class RehabRoutineOut(ORMBaseModel):
    id:          uuid.UUID
    plan_id:     Optional[uuid.UUID] = None
    name:        str
    order_index: int = 0
    exercises:   List[RehabRoutineExerciseOut] = []


# ──────────────────────────────────────────
# Rehab Plan schemas
# ──────────────────────────────────────────

class RehabPlanCreate(BaseModel):
    """POST /rehab/plans — create a new rehab plan."""
    title:        str
    description:  Optional[str] = None
    condition_id: Optional[uuid.UUID] = None


class RehabPlanUpdate(BaseModel):
    """PATCH /rehab/plans/{plan_id} — partial update."""
    title:        Optional[str] = None
    description:  Optional[str] = None
    condition_id: Optional[uuid.UUID] = None
    is_active:    Optional[bool] = None


class RehabPlanListItem(ORMBaseModel):
    """Summary card for the plan list (no nested data)."""
    id:           uuid.UUID
    title:        str
    description:  Optional[str] = None
    is_active:    Optional[bool] = True
    condition_id: Optional[uuid.UUID] = None
    condition:    Optional[RehabConditionOut] = None
    created_at:   Optional[datetime] = None
    updated_at:   Optional[datetime] = None


class RehabPlanOut(ORMBaseModel):
    """Full plan with nested routines and their exercises."""
    id:           uuid.UUID
    user_id:      Optional[uuid.UUID] = None
    title:        str
    description:  Optional[str] = None
    is_active:    Optional[bool] = True
    condition_id: Optional[uuid.UUID] = None
    condition:    Optional[RehabConditionOut] = None
    routines:     List[RehabRoutineOut] = []
    created_at:   Optional[datetime] = None
    updated_at:   Optional[datetime] = None
