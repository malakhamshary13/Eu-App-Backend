import uuid
from datetime import date
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from modules.daily_logs.models import DailyLog
from modules.daily_logs.schemas import DailyLogUpdate, DailyLogUpsert


class DailyLogRepository:
    """
    DB operations for tracker.daily_logs.

    Invariants:
      1. One log per (user_id, date) — enforced by DB unique constraint.
         The upsert operation handles conflicts gracefully.
      2. calories_consumed >= 0 and workouts_completed >= 0.
      3. Logs cannot be hard-deleted — they are permanent daily records.
         (Admins / system may clear them, but users cannot.)
    """

    # ──────────────────────────────────────────────────────────────────────────
    # Guards
    # ──────────────────────────────────────────────────────────────────────────

    def _get_log_or_404(
        self, db: Session, log_date: date, user_id: uuid.UUID
    ) -> DailyLog:
        log = (
            db.query(DailyLog)
            .filter(DailyLog.user_id == user_id, DailyLog.date == log_date)
            .first()
        )
        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No daily log found for {log_date}.",
            )
        return log

    # ──────────────────────────────────────────────────────────────────────────
    # Upsert (create or update for a given date)
    # ──────────────────────────────────────────────────────────────────────────

    def upsert_log(
        self, db: Session, user_id: uuid.UUID, data: DailyLogUpsert
    ) -> DailyLog:
        """
        Create a new daily log, or update the existing one for the same date.
        Only non-None fields are applied on update so callers can patch
        individual columns without overwriting others.
        """
        existing = (
            db.query(DailyLog)
            .filter(DailyLog.user_id == user_id, DailyLog.date == data.date)
            .first()
        )

        if existing:
            # Update only the fields that were explicitly provided
            if data.calories_consumed is not None:
                existing.calories_consumed = data.calories_consumed
            if data.workouts_completed is not None:
                existing.workouts_completed = data.workouts_completed
            if data.recovery_notes is not None:
                existing.recovery_notes = data.recovery_notes
            db.commit()
            db.refresh(existing)
            return existing

        # New log for this date
        log = DailyLog(
            user_id=user_id,
            date=data.date,
            calories_consumed=data.calories_consumed,
            workouts_completed=data.workouts_completed,
            recovery_notes=data.recovery_notes,
        )
        db.add(log)
        try:
            db.commit()
        except IntegrityError:
            # Race condition: another request created the row between our
            # SELECT and INSERT. Roll back and return the now-existing row.
            db.rollback()
            return self._get_log_or_404(db, data.date, user_id)
        db.refresh(log)
        return log

    # ──────────────────────────────────────────────────────────────────────────
    # Read
    # ──────────────────────────────────────────────────────────────────────────

    def get_log_by_date(
        self, db: Session, log_date: date, user_id: uuid.UUID
    ) -> DailyLog:
        return self._get_log_or_404(db, log_date, user_id)

    def list_logs(
        self,
        db: Session,
        user_id: uuid.UUID,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[DailyLog]:
        q = db.query(DailyLog).filter(DailyLog.user_id == user_id)
        if from_date:
            q = q.filter(DailyLog.date >= from_date)
        if to_date:
            q = q.filter(DailyLog.date <= to_date)
        return q.order_by(DailyLog.date.desc()).all()

    # ──────────────────────────────────────────────────────────────────────────
    # Patch (partial update of an existing log)
    # ──────────────────────────────────────────────────────────────────────────

    def patch_log(
        self,
        db: Session,
        log_date: date,
        user_id: uuid.UUID,
        data: DailyLogUpdate,
    ) -> DailyLog:
        """Update only the supplied fields on the existing log for `log_date`."""
        log = self._get_log_or_404(db, log_date, user_id)
        if data.calories_consumed is not None:
            log.calories_consumed = data.calories_consumed
        if data.workouts_completed is not None:
            log.workouts_completed = data.workouts_completed
        if data.recovery_notes is not None:
            log.recovery_notes = data.recovery_notes
        db.commit()
        db.refresh(log)
        return log
