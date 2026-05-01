import uuid
from typing import Optional, List
from pydantic import BaseModel, Field


# ──────────────────────────────────────────
# Nested / shared
# ──────────────────────────────────────────

class SecondaryMuscleOut(BaseModel):
    id: uuid.UUID
    muscle_name: str

    class Config:
        from_attributes = True


# ──────────────────────────────────────────
# Response schemas
# ──────────────────────────────────────────

class ExerciseResponse(BaseModel):
    """Full exercise record returned by the API."""
    id: uuid.UUID
    source_id: Optional[str] = None
    title: str
    exercise_type: Optional[str] = None       # 'weight_reps' | 'reps_only' | 'duration'
    muscle_group: Optional[str] = None         # primary muscle group
    equipment_category: Optional[str] = None   # 'barbell' | 'dumbbell' | 'machine' | 'none'
    url: Optional[str] = None
    media_type: Optional[str] = None
    thumbnail_url: Optional[str] = None
    instructions: Optional[str] = None
    manual_tag: Optional[str] = None
    priority: int = 0
    is_custom: bool = False
    is_archived: bool = False
    hundred_percent_bodyweight: bool = False
    secondary_muscles: List[SecondaryMuscleOut] = []

    class Config:
        from_attributes = True


class PaginatedExercises(BaseModel):
    """Paginated list of exercises."""
    items: List[ExerciseResponse]
    total: int
    page: int
    page_size: int
    pages: int          # total number of pages


# ──────────────────────────────────────────
# Request / input schemas
# ──────────────────────────────────────────

class ExerciseCreate(BaseModel):
    """Payload for POST /exercises/ (admin only)."""
    title: str
    exercise_type: Optional[str] = None
    muscle_group: Optional[str] = None
    equipment_category: Optional[str] = None
    url: Optional[str] = None
    media_type: Optional[str] = None
    thumbnail_url: Optional[str] = None
    instructions: Optional[str] = None
    manual_tag: Optional[str] = None
    priority: int = 0
    is_custom: bool = False
    hundred_percent_bodyweight: bool = False
    secondary_muscles: List[str] = []          # list of muscle_name strings


class ExerciseUpdate(BaseModel):
    """Payload for PUT /exercises/{id} (admin only). All fields optional."""
    title: Optional[str] = None
    exercise_type: Optional[str] = None
    muscle_group: Optional[str] = None
    equipment_category: Optional[str] = None
    url: Optional[str] = None
    media_type: Optional[str] = None
    thumbnail_url: Optional[str] = None
    instructions: Optional[str] = None
    manual_tag: Optional[str] = None
    priority: Optional[int] = None
    is_custom: Optional[bool] = None
    is_archived: Optional[bool] = None
    hundred_percent_bodyweight: Optional[bool] = None
    secondary_muscles: Optional[List[str]] = None  # None = don't touch, [] = clear all
