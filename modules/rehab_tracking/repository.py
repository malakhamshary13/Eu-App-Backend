import json
import uuid
from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from modules.rehab_tracking.models import RehabSession, RehabSessionExercise
from modules.rehab_tracking.schemas import (
    VALID_TRANSITIONS,
    RehabSessionCreate,
    RehabSessionStatusUpdate,
    SessionExerciseUpdate,
)
from modules.rehab.models import RehabRoutine, RehabRoutineExercise


class RehabTrackingRepository:
    """
    All DB operations for the rehab tracking module.

    Invariants (mirrors workout_tracking rules, adapted for rehab):
      1. Users can only read/modify their own sessions.
      2. Status transitions are strictly forward-only.
      3. Exercise logs can only be updated while session is 'in_progress'.
      4. A session cannot be completed with zero exercises marked done.
      5. Completed / skipped sessions are immutable.
    """

    # ──────────────────────────────────────────
    # Internal guards
    # ──────────────────────────────────────────

    def _get_session_or_404(
        self, db: Session, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> RehabSession:
        s = (
            db.query(RehabSession)
            .filter(
                RehabSession.id == session_id,
                RehabSession.user_id == user_id,
            )
            .first()
        )
        if not s:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rehab session {session_id} not found.",
            )
        return s

    def _require_in_progress(self, session: RehabSession) -> None:
        if session.status != "in_progress":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Cannot modify exercises on a session with status "
                    f"'{session.status}'. Session must be 'in_progress'."
                ),
            )

    def _get_session_exercise_or_404(
        self, db: Session, entry_id: uuid.UUID, session: RehabSession
    ) -> RehabSessionExercise:
        entry = (
            db.query(RehabSessionExercise)
            .filter(
                RehabSessionExercise.id == entry_id,
                RehabSessionExercise.session_id == session.id,
            )
            .first()
        )
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session exercise {entry_id} not found in this session.",
            )
        return entry

    # ──────────────────────────────────────────
    # Sessions — Create
    # ──────────────────────────────────────────

    def create_session(
        self, db: Session, user_id: uuid.UUID, data: RehabSessionCreate
    ) -> RehabSession:
        """
        Create a new rehab session and auto-populate exercise logs from the
        routine's prescribed exercises (rehab_routine_exercises).
        """
        # Validate routine belongs to the plan
        routine = (
            db.query(RehabRoutine)
            .filter(
                RehabRoutine.id == data.routine_id,
                RehabRoutine.plan_id == data.plan_id,
            )
            .first()
        )
        if not routine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Routine {data.routine_id} not found in plan {data.plan_id}. "
                    "Verify both IDs are correct."
                ),
            )

        now_utc = datetime.now(timezone.utc)

        session = RehabSession(
            user_id=user_id,
            plan_id=data.plan_id,
            routine_id=data.routine_id,
            scheduled_date=data.scheduled_date or date.today(),
            status=data.status,
            started_at=now_utc if data.status == "in_progress" else None,
        )
        db.add(session)
        db.flush()  # get session.id before inserting children

        # Auto-populate exercise logs from the routine prescription
        prescribed = (
            db.query(RehabRoutineExercise)
            .filter(RehabRoutineExercise.routine_id == data.routine_id)
            .order_by(RehabRoutineExercise.order_index)
            .all()
        )
        for rx in prescribed:
            log = RehabSessionExercise(
                session_id=session.id,
                routine_exercise_id=rx.id,
                exercise_id=rx.exercise_id,
                is_completed=False,
            )
            db.add(log)

        db.commit()
        db.refresh(session)
        return session

    # ──────────────────────────────────────────
    # Sessions — Read
    # ──────────────────────────────────────────

    def get_session(
        self, db: Session, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> RehabSession:
        return self._get_session_or_404(db, session_id, user_id)

    def list_sessions(
        self,
        db: Session,
        user_id: uuid.UUID,
        session_status: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        plan_id: Optional[uuid.UUID] = None,
    ) -> List[RehabSession]:
        q = db.query(RehabSession).filter(RehabSession.user_id == user_id)

        if session_status:
            q = q.filter(RehabSession.status == session_status)
        if from_date:
            q = q.filter(RehabSession.scheduled_date >= from_date)
        if to_date:
            q = q.filter(RehabSession.scheduled_date <= to_date)
        if plan_id:
            q = q.filter(RehabSession.plan_id == plan_id)

        return q.order_by(RehabSession.scheduled_date.desc()).all()

    # ──────────────────────────────────────────
    # Sessions — Status transitions
    # ──────────────────────────────────────────

    def update_session_status(
        self,
        db: Session,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        data: RehabSessionStatusUpdate,
    ) -> RehabSession:
        """
        Advance the session lifecycle. Rules:
          • scheduled   → in_progress | skipped
          • in_progress → completed
          • completed / skipped → immutable (terminal)
          • 'completed' requires at least 1 exercise marked is_completed=True
        """
        session = self._get_session_or_404(db, session_id, user_id)
        current = session.status
        target = data.status

        # Forward-only guard
        if target not in VALID_TRANSITIONS.get(current, set()):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Cannot transition from '{current}' to '{target}'. "
                    f"Allowed next states: "
                    f"{sorted(VALID_TRANSITIONS.get(current, set())) or 'none (terminal)'}."
                ),
            )

        # Must have at least one exercise completed before finishing
        if target == "completed":
            done = sum(1 for ex in session.exercises if ex.is_completed)
            if done == 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Cannot complete a session with no exercises marked as done. "
                        "Mark at least one exercise as completed first."
                    ),
                )

        now_utc = datetime.now(timezone.utc)
        session.status = target

        if target == "in_progress" and session.started_at is None:
            session.started_at = now_utc

        if target == "completed":
            session.completed_at = data.completed_at or now_utc
            if data.pain_level is not None:
                session.pain_level = data.pain_level
            if data.notes is not None:
                session.notes = data.notes

        db.commit()
        db.refresh(session)
        return session

    # ──────────────────────────────────────────
    # Sessions — Delete
    # ──────────────────────────────────────────

    def delete_session(
        self, db: Session, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> dict:
        """
        Delete a session and all its exercise logs.
        Completed sessions are permanent records — cannot be deleted.
        """
        session = self._get_session_or_404(db, session_id, user_id)
        if session.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Completed rehab sessions cannot be deleted. "
                    "They are permanent recovery records."
                ),
            )
        db.delete(session)
        db.commit()
        return {"detail": f"Rehab session {session_id} deleted."}

    # ──────────────────────────────────────────
    # Session Exercises — Update
    # ──────────────────────────────────────────

    def update_session_exercise(
        self,
        db: Session,
        session_id: uuid.UUID,
        entry_id: uuid.UUID,
        user_id: uuid.UUID,
        data: SessionExerciseUpdate,
    ) -> RehabSessionExercise:
        """
        Log/update performance for a single exercise within an in_progress session.
        Only provided (non-None) fields are changed.
        """
        session = self._get_session_or_404(db, session_id, user_id)
        self._require_in_progress(session)
        entry = self._get_session_exercise_or_404(db, entry_id, session)

        if data.sets_completed is not None:
            entry.sets_completed = data.sets_completed
        if data.reps_completed is not None:
            entry.reps_completed = data.reps_completed
        if data.hold_time_seconds is not None:
            entry.hold_time_seconds = data.hold_time_seconds
        if data.is_completed is not None:
            entry.is_completed = data.is_completed
        if data.pain_level is not None:
            entry.pain_level = data.pain_level
        if data.notes is not None:
            entry.notes = data.notes

        db.commit()
        db.refresh(entry)
        return entry

    def get_session_exercises(
        self,
        db: Session,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> List[RehabSessionExercise]:
        """Return all exercise logs for a session."""
        session = self._get_session_or_404(db, session_id, user_id)
        return (
            db.query(RehabSessionExercise)
            .filter(RehabSessionExercise.session_id == session.id)
            .all()
        )

    # ──────────────────────────────────────────
    # Analytics — DB stored procedures
    # ──────────────────────────────────────────
    # The procedures use auth.uid() for row-level security.
    # Since SQLAlchemy connects directly (not via PostgREST),
    # we SET LOCAL request.jwt.claims within the same transaction
    # so that auth.uid() resolves to the correct user.
    # ──────────────────────────────────────────

    def _set_auth_uid(self, db: Session, user_id: uuid.UUID) -> None:
        """Inject auth.uid() for the current transaction so RLS procedures work."""
        claims = json.dumps({"sub": str(user_id)})
        db.execute(
            text("SELECT set_config('request.jwt.claims', :claims, true)"),
            {"claims": claims},
        )

    def get_streaks(self, db: Session, user_id: uuid.UUID) -> dict:
        """
        Call tracker.get_rehab_streaks().
        Returns: current_streak, longest_streak, last_active_day.
        """
        self._set_auth_uid(db, user_id)
        row = db.execute(text("SELECT * FROM tracker.get_rehab_streaks()")).fetchone()
        if not row:
            return {"current_streak": 0, "longest_streak": 0, "last_active_day": None}
        return {
            "current_streak":  row.current_streak,
            "longest_streak":  row.longest_streak,
            "last_active_day": row.last_active_day,
        }

    def get_session_detail(self, db: Session, session_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        """
        Call tracker.get_rehab_session_detail(p_session_id).
        Returns full session metadata plus per-exercise planned vs. actual.
        """
        self._set_auth_uid(db, user_id)
        rows = db.execute(
            text("SELECT * FROM tracker.get_rehab_session_detail(:sid)"),
            {"sid": str(session_id)},
        ).fetchall()

        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found or does not belong to you.",
            )

        first = rows[0]
        exercises = [
            {
                "session_exercise_id":  r.session_exercise_id,
                "exercise_id":          r.exercise_id,
                "exercise_title":       r.exercise_title,
                "order_index":          r.order_index,
                "planned_sets":         r.planned_sets,
                "planned_reps":         r.planned_reps,
                "planned_hold_seconds": r.planned_hold_seconds,
                "sets_completed":       r.sets_completed,
                "reps_completed":       r.reps_completed,
                "hold_time_seconds":    r.hold_time_seconds,
                "is_completed":         r.is_completed,
                "pain_level":           r.pain_level,
                "notes":                r.notes,
            }
            for r in rows
            if r.session_exercise_id is not None
        ]

        return {
            "session_id":          first.session_id,
            "scheduled_date":      first.scheduled_date,
            "routine_name":        first.routine_name,
            "session_status":      first.session_status,
            "session_pain_level":  first.session_pain_level,
            "session_notes":       first.session_notes,
            "started_at":          first.started_at,
            "completed_at":        first.completed_at,
            "total_exercises":     int(first.total_exercises) if first.total_exercises else 0,
            "exercises_completed": int(first.exercises_completed) if first.exercises_completed else 0,
            "exercises":           exercises,
        }

    def get_exercise_progress(
        self, db: Session, exercise_id: uuid.UUID, user_id: uuid.UUID
    ) -> dict:
        """
        Call tracker.get_rehab_exercise_progress(p_exercise_id).
        Returns a timeline of planned vs. actual performance for one exercise.
        """
        self._set_auth_uid(db, user_id)
        rows = db.execute(
            text("SELECT * FROM tracker.get_rehab_exercise_progress(:eid)"),
            {"eid": str(exercise_id)},
        ).fetchall()

        return {
            "exercise_id": exercise_id,
            "timeline": [
                {
                    "session_id":        r.session_id,
                    "scheduled_date":    r.scheduled_date,
                    "routine_name":      r.name,
                    "planned_sets":      r.planned_sets,
                    "planned_reps":      r.planned_reps,
                    "planned_hold_secs": r.hold_time_seconds,
                    "sets_completed":    r.sets_completed,
                    "reps_completed":    r.reps_completed,
                    "hold_time_seconds": r.hold_time_seconds,
                    "is_completed":      r.is_completed,
                    "pain_level":        r.pain_level,
                    "notes":             r.notes,
                }
                for r in rows
            ],
        }

    def get_history(self, db: Session, user_id: uuid.UUID) -> dict:
        """
        Call tracker.get_rehab_completed_sessions().
        Returns all completed sessions with per-exercise breakdown, grouped by session.
        """
        self._set_auth_uid(db, user_id)
        rows = db.execute(
            text("SELECT * FROM tracker.get_rehab_completed_sessions()")
        ).fetchall()

        # Group flat rows by session_id
        sessions: dict = {}
        for r in rows:
            sid = str(r.session_id)
            if sid not in sessions:
                sessions[sid] = {
                    "session_id":          r.session_id,
                    "plan_id":             r.plan_id,
                    "routine_id":          r.routine_id,
                    "routine_name":        r.routine_name,
                    "scheduled_date":      r.scheduled_date,
                    "started_at":          r.started_at,
                    "completed_at":        r.completed_at,
                    "session_pain_level":  r.session_pain_level,
                    "session_notes":       r.session_notes,
                    "total_exercises":     int(r.total_exercises) if r.total_exercises else 0,
                    "exercises_completed": int(r.exercises_completed) if r.exercises_completed else 0,
                    "exercises":           [],
                }
            if r.session_exercise_id is not None:
                sessions[sid]["exercises"].append({
                    "session_exercise_id":   r.session_exercise_id,
                    "exercise_id":           r.exercise_id,
                    "exercise_title":        r.exercise_title,
                    "sets_completed":        r.sets_completed,
                    "reps_completed":        r.reps_completed,
                    "hold_time_seconds":     r.hold_time_seconds,
                    "exercise_is_completed": r.exercise_is_completed,
                    "exercise_pain_level":   r.exercise_pain_level,
                    "exercise_notes":        r.exercise_notes,
                })

        result = list(sessions.values())
        return {"total": len(result), "results": result}
