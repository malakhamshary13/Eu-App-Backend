import uuid
from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from modules.workout_tracking.models import WorkoutSession, WorkoutSessionItem
from modules.workout_tracking.schemas import (
    VALID_TRANSITIONS,
    SessionCreate,
    SessionItemCreate,
    SessionItemUpdate,
    SessionStatusUpdate,
)


class WorkoutTrackingRepository:
    """
    All database operations for the workout tracking module.

    Invariants enforced here (medical-grade rules):
      1. A user can only read/modify their own sessions.
      2. Status transitions are strictly forward-only (no rollbacks).
      3. Items (sets) can only be added to an 'in_progress' session.
      4. A session cannot be marked 'completed' if it has zero items.
      5. set_number must be ≥ 1; the same (session, exercise, set_number)
         triple must be unique — a duplicate set_number for the same exercise
         within the same session is rejected.
      6. reps_completed ≥ 0 and weight_used ≥ 0 (also enforced by DB CHECK).
      7. Completed / abandoned / skipped sessions are immutable — no items
         can be added or deleted once in a terminal state.
    """

    # ──────────────────────────────────────────────────────────────────────────
    # Internal guards
    # ──────────────────────────────────────────────────────────────────────────

    def _get_session_or_404(
        self, db: Session, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkoutSession:
        session = (
            db.query(WorkoutSession)
            .filter(
                WorkoutSession.id == session_id,
                WorkoutSession.user_id == user_id,
            )
            .first()
        )
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workout session {session_id} not found.",
            )
        return session

    def _require_in_progress(self, session: WorkoutSession) -> None:
        """Items may only be logged while the session is actively in progress."""
        if session.status != "in_progress":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Cannot modify items on a session with status "
                    f"'{session.status}'. Session must be 'in_progress'."
                ),
            )

    def _get_item_or_404(
        self, db: Session, item_id: uuid.UUID, session: WorkoutSession
    ) -> WorkoutSessionItem:
        item = (
            db.query(WorkoutSessionItem)
            .filter(
                WorkoutSessionItem.id == item_id,
                WorkoutSessionItem.session_id == session.id,
            )
            .first()
        )
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session item {item_id} not found in this session.",
            )
        return item

    # ──────────────────────────────────────────────────────────────────────────
    # Sessions — Create
    # ──────────────────────────────────────────────────────────────────────────

    def create_session(
        self,
        db: Session,
        user_id: uuid.UUID,
        data: SessionCreate,
    ) -> WorkoutSession:
        """Create a new workout session, optionally linked to a plan/routine."""
        now_utc = datetime.now(timezone.utc)

        session = WorkoutSession(
            user_id=user_id,
            workout_plan_id=data.workout_plan_id,
            routine_id=data.routine_id,
            scheduled_date=data.scheduled_date or date.today(),
            status=data.status,
            started_at=now_utc if data.status == "in_progress" else None,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    # ──────────────────────────────────────────────────────────────────────────
    # Sessions — Read
    # ──────────────────────────────────────────────────────────────────────────

    def get_session(
        self, db: Session, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkoutSession:
        return self._get_session_or_404(db, session_id, user_id)

    def list_sessions(
        self,
        db: Session,
        user_id: uuid.UUID,
        session_status: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        workout_plan_id: Optional[uuid.UUID] = None,
    ) -> List[WorkoutSession]:
        q = db.query(WorkoutSession).filter(WorkoutSession.user_id == user_id)

        if session_status:
            q = q.filter(WorkoutSession.status == session_status)
        if from_date:
            q = q.filter(WorkoutSession.scheduled_date >= from_date)
        if to_date:
            q = q.filter(WorkoutSession.scheduled_date <= to_date)
        if workout_plan_id:
            q = q.filter(WorkoutSession.workout_plan_id == workout_plan_id)

        return q.order_by(WorkoutSession.scheduled_date.desc()).all()

    # ──────────────────────────────────────────────────────────────────────────
    # Sessions — Status transitions
    # ──────────────────────────────────────────────────────────────────────────

    def update_session_status(
        self,
        db: Session,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        data: SessionStatusUpdate,
    ) -> WorkoutSession:
        """
        Advance the session status.  Rules:
          • scheduled   → in_progress | skipped
          • in_progress → completed   | abandoned
          • completed / abandoned / skipped → immutable (reject)
          • 'completed' requires ≥ 1 logged item
        """
        session = self._get_session_or_404(db, session_id, user_id)
        current = session.status
        target  = data.status

        # Enforce forward-only transition
        if target not in VALID_TRANSITIONS.get(current, set()):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Cannot transition from '{current}' to '{target}'. "
                    f"Allowed next states: {sorted(VALID_TRANSITIONS[current]) or 'none (terminal)'}."
                ),
            )

        # Must have at least one logged set before completing
        if target == "completed" and not session.items:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Cannot complete a session with no logged sets. "
                    "Log at least one exercise set before completing."
                ),
            )

        now_utc = datetime.now(timezone.utc)
        session.status = target

        if target == "in_progress" and session.started_at is None:
            session.started_at = now_utc

        if target == "completed":
            session.completed_at = data.completed_at or now_utc

        db.commit()
        db.refresh(session)
        return session

    # ──────────────────────────────────────────────────────────────────────────
    # Sessions — Delete
    # ──────────────────────────────────────────────────────────────────────────

    def delete_session(
        self, db: Session, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> dict:
        """
        Delete a session and all its items (cascade).
        Completed sessions are protected — they are permanent records.
        """
        session = self._get_session_or_404(db, session_id, user_id)

        if session.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Completed sessions cannot be deleted. "
                    "They are permanent performance records."
                ),
            )

        db.delete(session)
        db.commit()
        return {"detail": f"Workout session {session_id} deleted."}

    # ──────────────────────────────────────────────────────────────────────────
    # Session Items — Create (single set)
    # ──────────────────────────────────────────────────────────────────────────

    def log_set(
        self,
        db: Session,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        data: SessionItemCreate,
    ) -> WorkoutSessionItem:
        """
        Log a single set.
        Rejects duplicate (exercise_id, set_number) within the same session.
        """
        session = self._get_session_or_404(db, session_id, user_id)
        self._require_in_progress(session)

        # Duplicate set guard
        duplicate = (
            db.query(WorkoutSessionItem)
            .filter(
                WorkoutSessionItem.session_id == session_id,
                WorkoutSessionItem.exercise_id == data.exercise_id,
                WorkoutSessionItem.set_number == data.set_number,
            )
            .first()
        )
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Set #{data.set_number} for exercise {data.exercise_id} "
                    f"already exists in this session. "
                    f"Use PATCH to update it, or choose the next set number."
                ),
            )

        item = WorkoutSessionItem(
            session_id=session_id,
            exercise_id=data.exercise_id,
            set_number=data.set_number,
            reps_completed=data.reps_completed,
            weight_used=data.weight_used,
            is_completed=data.is_completed,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    # ──────────────────────────────────────────────────────────────────────────
    # Session Items — Bulk create (all sets of one exercise)
    # ──────────────────────────────────────────────────────────────────────────

    def log_sets_bulk(
        self,
        db: Session,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        exercise_id: uuid.UUID,
        sets: List[SessionItemCreate],
    ) -> List[WorkoutSessionItem]:
        """
        Log all sets of a single exercise atomically.
        All set_numbers must be unique for this exercise within this session.
        """
        session = self._get_session_or_404(db, session_id, user_id)
        self._require_in_progress(session)

        # Validate uniqueness of set numbers within the request itself
        incoming_set_nums = [s.set_number for s in sets]
        if len(incoming_set_nums) != len(set(incoming_set_nums)):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Duplicate set_number values within the bulk request.",
            )

        # Check for conflicts against DB
        existing_set_nums = {
            row.set_number
            for row in db.query(WorkoutSessionItem.set_number)
            .filter(
                WorkoutSessionItem.session_id == session_id,
                WorkoutSessionItem.exercise_id == exercise_id,
            )
            .all()
        }
        conflicts = set(incoming_set_nums) & existing_set_nums
        if conflicts:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Set numbers {sorted(conflicts)} already exist for this exercise "
                    f"in the session. Use PATCH to update them."
                ),
            )

        items = [
            WorkoutSessionItem(
                session_id=session_id,
                exercise_id=exercise_id,
                set_number=s.set_number,
                reps_completed=s.reps_completed,
                weight_used=s.weight_used,
                is_completed=s.is_completed,
            )
            for s in sets
        ]
        db.add_all(items)
        db.commit()
        for item in items:
            db.refresh(item)
        return items

    # ──────────────────────────────────────────────────────────────────────────
    # Session Items — Read
    # ──────────────────────────────────────────────────────────────────────────

    def get_session_items(
        self,
        db: Session,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> List[WorkoutSessionItem]:
        """Return all items for a session ordered by exercise then set_number."""
        session = self._get_session_or_404(db, session_id, user_id)
        return (
            db.query(WorkoutSessionItem)
            .filter(WorkoutSessionItem.session_id == session.id)
            .order_by(
                WorkoutSessionItem.exercise_id,
                WorkoutSessionItem.set_number,
            )
            .all()
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Session Items — Update (correct a set)
    # ──────────────────────────────────────────────────────────────────────────

    def update_set(
        self,
        db: Session,
        session_id: uuid.UUID,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
        data: SessionItemUpdate,
    ) -> WorkoutSessionItem:
        """
        Correct a logged set.  Allowed in 'in_progress' sessions only.
        Only provided (non-None) fields are changed.
        """
        session = self._get_session_or_404(db, session_id, user_id)
        self._require_in_progress(session)
        item = self._get_item_or_404(db, item_id, session)

        if data.reps_completed is not None:
            item.reps_completed = data.reps_completed
        if data.weight_used is not None:
            item.weight_used = data.weight_used
        if data.is_completed is not None:
            item.is_completed = data.is_completed

        db.commit()
        db.refresh(item)
        return item

    # ──────────────────────────────────────────────────────────────────────────
    # Session Items — Delete
    # ──────────────────────────────────────────────────────────────────────────

    def delete_set(
        self,
        db: Session,
        session_id: uuid.UUID,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict:
        """
        Remove a logged set.  Allowed only while session is 'in_progress'
        so that completed records remain intact.
        """
        session = self._get_session_or_404(db, session_id, user_id)
        self._require_in_progress(session)
        item = self._get_item_or_404(db, item_id, session)
        db.delete(item)
        db.commit()
        return {"detail": f"Set {item_id} removed from session."}
