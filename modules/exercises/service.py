import uuid
from typing import Optional

from sqlalchemy.orm import Session

from modules.exercises.repository import ExerciseRepository
from modules.exercises.schemas import (
    ExerciseCreate, ExerciseUpdate, ExerciseResponse, PaginatedExercises, FilterOptions,
)

_repo = ExerciseRepository()


class ExerciseService:
    """Business logic layer for the exercises module."""

    def get_filter_options(self, db: Session) -> FilterOptions:
        """Return distinct non-null filter values from the live DB."""
        return _repo.get_filter_options(db)

    def list_exercises(
        self,
        db: Session,
        *,
        page: int,
        page_size: int,
        exercise_type: Optional[str],
        muscle_group: Optional[str],
        equipment_category: Optional[str],
        search: Optional[str],
        hundred_percent_bodyweight: Optional[bool],
        is_custom: Optional[bool],
        use_profile: bool,
        user_id: Optional[uuid.UUID],
    ) -> PaginatedExercises:
        """
        Return a paginated exercise list.
        If use_profile=True, passes user_id to the repo so filters
        are auto-derived from the user's health profile goal.
        """
        return _repo.get_exercises(
            db,
            page=page,
            page_size=page_size,
            exercise_type=exercise_type,
            muscle_group=muscle_group,
            equipment_category=equipment_category,
            search=search,
            hundred_percent_bodyweight=hundred_percent_bodyweight,
            is_custom=is_custom,
            user_id=user_id if use_profile else None,
        )

    def get_exercise(self, db: Session, exercise_id: uuid.UUID) -> ExerciseResponse:
        return _repo.get_by_id(db, exercise_id)

    def create_exercise(self, db: Session, data: ExerciseCreate) -> ExerciseResponse:
        return _repo.create_exercise(db, data)

    def update_exercise(
        self, db: Session, exercise_id: uuid.UUID, data: ExerciseUpdate
    ) -> ExerciseResponse:
        return _repo.update_exercise(db, exercise_id, data)

    def delete_exercise(self, db: Session, exercise_id: uuid.UUID) -> dict:
        return _repo.delete_exercise(db, exercise_id)
