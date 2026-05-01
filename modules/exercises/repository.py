import math
import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from modules.exercises.models import Exercise, ExerciseSecondaryMuscle
from modules.exercises.schemas import ExerciseCreate, ExerciseUpdate, PaginatedExercises
from modules.users.models import HealthProfile


# Maps a user's primary_goal to exercise filters
# so that "filter by health profile" returns relevant exercises.
_GOAL_FILTERS = {
    "weight_loss":    {"exercise_type": None,           "equipment_category": "barbell"},
    "muscle_gain":    {"exercise_type": "weight_reps",  "equipment_category": "machine"},
    "rehab":          {"exercise_type": "reps_only",    "equipment_category": "resistance_band"},
    "maintenance":    {"exercise_type": None,           "equipment_category": None},
}


class ExerciseRepository:
    """Handles all DB operations for the exercises module."""

    # ──────────────────────────────────────────
    # Read
    # ──────────────────────────────────────────

    def get_exercises(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 20,
        exercise_type: Optional[str] = None,
        muscle_group: Optional[str] = None,
        equipment_category: Optional[str] = None,
        search: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,   # when set, auto-filter by health profile
        include_archived: bool = False,
    ) -> PaginatedExercises:
        """
        Return a paginated, optionally filtered list of exercises.

        Filter priority:
          1. user_id (health profile) provides defaults for exercise_type / equipment_category
          2. Explicit query params override those defaults
          3. muscle_group and search are always applied on top
        """
        # ── If user_id given, read health profile and derive defaults ──
        if user_id:
            profile = (
                db.query(HealthProfile)
                .filter(HealthProfile.user_id == user_id)
                .first()
            )
            if profile and profile.primary_goal:
                defaults = _GOAL_FILTERS.get(profile.primary_goal, {})
                # Only apply defaults when the caller hasn't specified that filter
                if exercise_type is None:
                    exercise_type = defaults.get("exercise_type")
                if equipment_category is None:
                    equipment_category = defaults.get("equipment_category")

        # ── Build query ──
        q = db.query(Exercise)

        if not include_archived:
            q = q.filter(Exercise.is_archived.is_(False))

        if exercise_type:
            q = q.filter(Exercise.exercise_type == exercise_type)

        if muscle_group:
            q = q.filter(Exercise.muscle_group == muscle_group)

        if equipment_category:
            q = q.filter(Exercise.equipment_category == equipment_category)

        if search:
            q = q.filter(Exercise.title.ilike(f"%{search}%"))

        # ── Pagination ──
        total = q.count()
        page_size = min(page_size, 100)   # hard cap at 100 per page
        offset = (page - 1) * page_size
        items = q.order_by(Exercise.priority.desc(), Exercise.title).offset(offset).limit(page_size).all()

        return PaginatedExercises(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=math.ceil(total / page_size) if total else 0,
        )

    def get_by_id(self, db: Session, exercise_id: uuid.UUID) -> Exercise:
        """Return a single exercise or raise 404."""
        exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
        if not exercise:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Exercise {exercise_id} not found.",
            )
        return exercise

    # ──────────────────────────────────────────
    # Write (admin only)
    # ──────────────────────────────────────────

    def create_exercise(self, db: Session, data: ExerciseCreate) -> Exercise:
        """Insert a new exercise row and its secondary muscles."""
        exercise = Exercise(
            title=data.title,
            exercise_type=data.exercise_type,
            muscle_group=data.muscle_group,
            equipment_category=data.equipment_category,
            url=data.url,
            media_type=data.media_type,
            thumbnail_url=data.thumbnail_url,
            instructions=data.instructions,
            manual_tag=data.manual_tag,
            priority=data.priority,
            is_custom=data.is_custom,
            hundred_percent_bodyweight=data.hundred_percent_bodyweight,
        )
        db.add(exercise)
        db.flush()   # get exercise.id before inserting secondary muscles

        for muscle_name in data.secondary_muscles:
            db.add(ExerciseSecondaryMuscle(
                exercise_id=exercise.id,
                muscle_name=muscle_name,
            ))

        db.commit()
        db.refresh(exercise)
        return exercise

    def update_exercise(
        self, db: Session, exercise_id: uuid.UUID, data: ExerciseUpdate
    ) -> Exercise:
        """Partial update of an exercise. Only non-None fields are changed."""
        exercise = self.get_by_id(db, exercise_id)

        for field, value in data.model_dump(exclude_none=True, exclude={"secondary_muscles"}).items():
            setattr(exercise, field, value)

        # Replace secondary muscles only when the field is explicitly passed
        if data.secondary_muscles is not None:
            # delete existing
            db.query(ExerciseSecondaryMuscle).filter(
                ExerciseSecondaryMuscle.exercise_id == exercise_id
            ).delete()
            # insert new ones
            for muscle_name in data.secondary_muscles:
                db.add(ExerciseSecondaryMuscle(
                    exercise_id=exercise_id,
                    muscle_name=muscle_name,
                ))

        db.commit()
        db.refresh(exercise)
        return exercise

    def delete_exercise(self, db: Session, exercise_id: uuid.UUID) -> dict:
        """Soft-delete (archive) an exercise instead of hard-deleting."""
        exercise = self.get_by_id(db, exercise_id)
        exercise.is_archived = True
        db.commit()
        return {"message": f"Exercise '{exercise.title}' archived successfully."}






# db.query(Excercise)
"""db.query(Exercise)
    │
    └─► SQLAlchemy looks up Exercise in Base.metadata
        │
        └─► Finds: schema='library', table='exercises', columns=[...]
            │
            └─► Generates SQL: SELECT library.exercises.* FROM library.exercises



// how is query executed in detail
first it looks at model's attributes:

1.Table name:        __tablename__ = "exercises"
2.Schema:            __table_args__ = {'schema': 'library'}
3.Column names:      Each Column(...) attribute
4.Column types:      String, UUID, Boolean, etc.
5.Primary key:       primary_key=True
6.Relationships:     relationship(...) — for joins

then looks at methods: .filter(), .order_by(), .offset(), .limit()

"""
