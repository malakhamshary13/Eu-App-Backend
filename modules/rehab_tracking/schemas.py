import uuid
from datetime import date, datetime
from typing import Optional, List, Set

from pydantic import BaseModel, field_validator
from db.database import ORMBaseModel


# ──────────────────────────────────────────
# Valid status transitions (forward-only)
# ──────────────────────────────────────────

VALID_TRANSITIONS: dict[str, Set[str]] = {
    "scheduled":   {"in_progress", "skipped"},
    "in_progress": {"completed"},
    "completed":   set(),   # terminal
    "skipped":     set(),   # terminal
}


# ──────────────────────────────────────────
# Embedded exercise detail
# ──────────────────────────────────────────

class RehabExerciseBrief(ORMBaseModel):
    id:            uuid.UUID
    slug:          str
    title:         str
    thumbnail_url: Optional[str] = None
    youtube_url:   Optional[str] = None
    media_type:    Optional[str] = None


# ──────────────────────────────────────────
# Session Exercise schemas
# ──────────────────────────────────────────

class SessionExerciseUpdate(BaseModel):
    """PATCH a single exercise log within a session."""
    sets_completed:    Optional[int] = None
    reps_completed:    Optional[int] = None
    hold_time_seconds: Optional[int] = None
    is_completed:      Optional[bool] = None
    pain_level:        Optional[int] = None   # 1–10
    notes:             Optional[str] = None

    @field_validator("pain_level")
    @classmethod
    def validate_pain(cls, v):
        if v is not None and not (1 <= v <= 10):
            raise ValueError("pain_level must be between 1 and 10")
        return v


class SessionExerciseResponse(ORMBaseModel):
    id:                   uuid.UUID
    session_id:           uuid.UUID
    routine_exercise_id:  uuid.UUID
    exercise_id:          uuid.UUID
    sets_completed:       Optional[int] = None
    reps_completed:       Optional[int] = None
    hold_time_seconds:    Optional[int] = None
    is_completed:         bool = False
    pain_level:           Optional[int] = None
    notes:                Optional[str] = None
    exercise:             Optional[RehabExerciseBrief] = None


# ──────────────────────────────────────────
# Session schemas
# ──────────────────────────────────────────

class RehabSessionCreate(BaseModel):
    """POST /tracker/rehab/sessions — start or schedule a rehab session."""
    plan_id:        uuid.UUID
    routine_id:     uuid.UUID
    scheduled_date: Optional[date] = None       # defaults to today
    status:         str = "scheduled"            # 'scheduled' | 'in_progress'

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in {"scheduled", "in_progress"}:
            raise ValueError("Initial status must be 'scheduled' or 'in_progress'.")
        return v


class RehabSessionStatusUpdate(BaseModel):
    """PATCH /tracker/rehab/sessions/{session_id}/status"""
    status:       str
    pain_level:   Optional[int] = None          # session-level pain on completion
    notes:        Optional[str] = None
    completed_at: Optional[datetime] = None     # override; defaults to now()

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        allowed = {"in_progress", "completed", "skipped"}
        if v not in allowed:
            raise ValueError(f"status must be one of: {sorted(allowed)}")
        return v

    @field_validator("pain_level")
    @classmethod
    def validate_pain(cls, v):
        if v is not None and not (1 <= v <= 10):
            raise ValueError("pain_level must be between 1 and 10")
        return v


class RehabSessionResponse(ORMBaseModel):
    id:             uuid.UUID
    user_id:        uuid.UUID
    plan_id:        uuid.UUID
    routine_id:     uuid.UUID
    scheduled_date: date
    status:         str
    started_at:     Optional[datetime] = None
    completed_at:   Optional[datetime] = None
    pain_level:     Optional[int] = None
    notes:          Optional[str] = None
    created_at:     datetime
    exercises:      List[SessionExerciseResponse] = []


class RehabSessionListResponse(ORMBaseModel):
    total:   int
    results: List[RehabSessionResponse]


# ──────────────────────────────────────────
# Analytics schemas — backed by DB procedures
# ──────────────────────────────────────────

class RehabStreaksResponse(BaseModel):
    """GET /tracker/rehab/streaks — tracker.get_rehab_streaks()"""
    current_streak:  int
    longest_streak:  int
    last_active_day: Optional[date] = None


class SessionExerciseDetail(BaseModel):
    """One exercise row inside a session detail response."""
    session_exercise_id:  Optional[uuid.UUID] = None
    exercise_id:          Optional[uuid.UUID] = None
    exercise_title:       Optional[str] = None
    order_index:          Optional[int] = None
    planned_sets:         Optional[int] = None
    planned_reps:         Optional[int] = None
    planned_hold_seconds: Optional[int] = None
    sets_completed:       Optional[int] = None
    reps_completed:       Optional[int] = None
    hold_time_seconds:    Optional[int] = None
    is_completed:         Optional[bool] = None
    pain_level:           Optional[int] = None
    notes:                Optional[str] = None


class RehabSessionDetailResponse(BaseModel):
    """GET /tracker/rehab/sessions/{id}/detail — tracker.get_rehab_session_detail()"""
    session_id:          Optional[uuid.UUID] = None
    scheduled_date:      Optional[date] = None
    routine_name:        Optional[str] = None
    session_status:      Optional[str] = None
    session_pain_level:  Optional[int] = None
    session_notes:       Optional[str] = None
    started_at:          Optional[datetime] = None
    completed_at:        Optional[datetime] = None
    total_exercises:     Optional[int] = None
    exercises_completed: Optional[int] = None
    exercises:           List[SessionExerciseDetail] = []


class ExerciseProgressEntry(BaseModel):
    """One data point inside an exercise progress timeline."""
    session_id:         Optional[uuid.UUID] = None
    scheduled_date:     Optional[date] = None
    routine_name:       Optional[str] = None
    planned_sets:       Optional[int] = None
    planned_reps:       Optional[int] = None
    planned_hold_secs:  Optional[int] = None
    sets_completed:     Optional[int] = None
    reps_completed:     Optional[int] = None
    hold_time_seconds:  Optional[int] = None
    is_completed:       Optional[bool] = None
    pain_level:         Optional[int] = None
    notes:              Optional[str] = None


class ExerciseProgressResponse(BaseModel):
    """GET /tracker/rehab/exercises/{exercise_id}/progress"""
    exercise_id: uuid.UUID
    timeline:    List[ExerciseProgressEntry] = []


class RehabHistoryExercise(BaseModel):
    """One exercise inside a history session entry."""
    session_exercise_id:  Optional[uuid.UUID] = None
    exercise_id:          Optional[uuid.UUID] = None
    exercise_title:       Optional[str] = None
    sets_completed:       Optional[int] = None
    reps_completed:       Optional[int] = None
    hold_time_seconds:    Optional[int] = None
    exercise_is_completed: Optional[bool] = None
    exercise_pain_level:  Optional[int] = None
    exercise_notes:       Optional[str] = None


class RehabHistoryEntry(BaseModel):
    """One completed session inside the history list."""
    session_id:          Optional[uuid.UUID] = None
    plan_id:             Optional[uuid.UUID] = None
    routine_id:          Optional[uuid.UUID] = None
    routine_name:        Optional[str] = None
    scheduled_date:      Optional[date] = None
    started_at:          Optional[datetime] = None
    completed_at:        Optional[datetime] = None
    session_pain_level:  Optional[int] = None
    session_notes:       Optional[str] = None
    total_exercises:     Optional[int] = None
    exercises_completed: Optional[int] = None
    exercises:           List[RehabHistoryExercise] = []


class RehabHistoryResponse(BaseModel):
    """GET /tracker/rehab/history — tracker.get_rehab_completed_sessions()"""
    total:   int
    results: List[RehabHistoryEntry] = []

