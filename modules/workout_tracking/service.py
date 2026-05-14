import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from modules.workout_tracking.repository import WorkoutTrackingRepository
from modules.workout_tracking.schemas import (
    SessionCreate,
    SessionItemCreate,
    SessionItemUpdate,
    SessionStatusUpdate,
)

_repo = WorkoutTrackingRepository()


class WorkoutTrackingService:
    """Thin orchestration layer — delegates to repository."""

    # Sessions
    def create_session(self, db: Session, user_id: uuid.UUID, data: SessionCreate):
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
        workout_plan_id: Optional[uuid.UUID] = None,
    ):
        return _repo.list_sessions(
            db, user_id, session_status, from_date, to_date, workout_plan_id
        )

    def update_session_status(
        self,
        db: Session,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        data: SessionStatusUpdate,
    ):
        return _repo.update_session_status(db, session_id, user_id, data)

    def delete_session(self, db: Session, session_id: uuid.UUID, user_id: uuid.UUID):
        return _repo.delete_session(db, session_id, user_id)

    # Session Items
    def log_set(
        self,
        db: Session,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        data: SessionItemCreate,
    ):
        return _repo.log_set(db, session_id, user_id, data)

    def log_sets_bulk(
        self,
        db: Session,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        exercise_id: uuid.UUID,
        sets: List[SessionItemCreate],
    ):
        return _repo.log_sets_bulk(db, session_id, user_id, exercise_id, sets)

    def get_session_items(
        self, db: Session, session_id: uuid.UUID, user_id: uuid.UUID
    ):
        return _repo.get_session_items(db, session_id, user_id)

    def update_set(
        self,
        db: Session,
        session_id: uuid.UUID,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
        data: SessionItemUpdate,
    ):
        return _repo.update_set(db, session_id, item_id, user_id, data)

    def delete_set(
        self,
        db: Session,
        session_id: uuid.UUID,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        return _repo.delete_set(db, session_id, item_id, user_id)
