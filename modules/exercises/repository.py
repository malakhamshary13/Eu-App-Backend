from sqlalchemy.orm import Session
from modules.exercises.models import Exercise


class ExerciseRepository:
    def get_exercises(self, db: Session, count: int):
        """Return *count* non-archived exercises ordered by priority (lowest = highest priority)."""
        return (
            db.query(Exercise)
            .filter(Exercise.IsArchived == False)
            .order_by(Exercise.Priority.asc())
            .limit(count)
            .all()
        )
