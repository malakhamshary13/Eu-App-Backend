from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from modules.exercises.repository import ExerciseRepository


class ExerciseService:
    def __init__(self):
        self.repo = ExerciseRepository()

    def get_exercises(self, db: Session, count: int):
        exercises = self.repo.get_exercises(db, count)

        if not exercises:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No exercises found"
            )

        return exercises
