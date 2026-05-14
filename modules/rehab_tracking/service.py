import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from modules.rehab_tracking.repository import RehabTrackingRepository
from modules.rehab_tracking.schemas import (
    RehabSessionCreate,
    RehabSessionStatusUpdate,
    SessionExerciseUpdate,
)

_repo = RehabTrackingRepository()


class RehabTrackingService:
    """Business logic layer for the rehab tracking module."""

    def create_session(self, db: Session, user_id: uuid.UUID, data: RehabSessionCreate):
        return _repo.create_session(db, user_id, data)

    def get_session(self, db: Session, session_id: uuid.UUID, user_id: uuid.UUID):
        return _repo.get_session(db, session_id, user_id)

    def list_sessions(
        self,
        db: Session,
        user_id: uuid.UUID,
        session_status: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        plan_id: Optional[uuid.UUID] = None,
    ):
        return _repo.list_sessions(db, user_id, session_status, from_date, to_date, plan_id)

    def update_session_status(
        self,
        db: Session,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        data: RehabSessionStatusUpdate,
    ):
        return _repo.update_session_status(db, session_id, user_id, data)

    def delete_session(self, db: Session, session_id: uuid.UUID, user_id: uuid.UUID):
        return _repo.delete_session(db, session_id, user_id)

    def get_session_exercises(self, db: Session, session_id: uuid.UUID, user_id: uuid.UUID):
        return _repo.get_session_exercises(db, session_id, user_id)

    def update_session_exercise(
        self,
        db: Session,
        session_id: uuid.UUID,
        entry_id: uuid.UUID,
        user_id: uuid.UUID,
        data: SessionExerciseUpdate,
    ):
        return _repo.update_session_exercise(db, session_id, entry_id, user_id, data)

    # ── Analytics (DB procedures) ──────────────────
    def get_streaks(self, db: Session, user_id: uuid.UUID):
        return _repo.get_streaks(db, user_id)

    def get_session_detail(self, db: Session, session_id: uuid.UUID, user_id: uuid.UUID):
        return _repo.get_session_detail(db, session_id, user_id)

    def get_exercise_progress(self, db: Session, exercise_id: uuid.UUID, user_id: uuid.UUID):
        return _repo.get_exercise_progress(db, exercise_id, user_id)

    def get_history(self, db: Session, user_id: uuid.UUID):
        return _repo.get_history(db, user_id)

