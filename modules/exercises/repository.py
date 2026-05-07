import math
import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from modules.exercises.models import Exercise, ExerciseSecondaryMuscle
from modules.exercises.schemas import ExerciseCreate, ExerciseUpdate, PaginatedExercises, FilterOptions
from modules.users.models import HealthProfile


# Maps a user's primary_goal to exercise filters.
# Each key holds a list of valid DB values (or None = no filter for that column).
# Explicit API query params always override these goal defaults.
_GOAL_FILTERS: dict[str, dict] = {
    "weight_loss": {
        "exercise_types": [
            "duration",
            "distance_duration",
            "steps_duration",
            "floors_duration",
            "reps_only",
            "bodyweight_reps",
        ],
        "muscle_groups": [
            "full_body",
            "cardio",
            "quadriceps",
            "glutes",
            "hamstrings",
            "abdominals",
            "calves",
        ],
        "equipment_categories": ["none", "resistance_band", "kettlebell"],
    },
    "muscle_gain": {
        "exercise_types": ["weight_reps", "bodyweight_assisted_reps"],
        "muscle_groups": [
            "chest",
            "lats",
            "upper_back",
            "biceps",
            "triceps",
            "shoulders",
            "quadriceps",
            "hamstrings",
            "glutes",
            "traps",
            "forearms",
        ],
        "equipment_categories": ["barbell", "dumbbell", "machine", "plate"],
    },
    "rehab": {
        "exercise_types": [
            "reps_only",
            "bodyweight_reps",
            "bodyweight_assisted_reps",
            "duration",
        ],
        "muscle_groups": [
            "lower_back",
            "glutes",
            "hamstrings",
            "quadriceps",
            "shoulders",
            "upper_back",
            "abductors",
            "adductors",
            "calves",
        ],
        "equipment_categories": ["resistance_band", "none", "suspension"],
    },
    "maintenance": {
        # No filters — return the full library for users in maintenance mode
        "exercise_types": None,
        "muscle_groups": None,
        "equipment_categories": None,
    },
}


class ExerciseRepository:
    """Handles all DB operations for the exercises module."""

    # ──────────────────────────────────────────
    # Read
    # ──────────────────────────────────────────

    def get_filter_options(self, db: Session) -> FilterOptions:
        """
        Return distinct non-null values for every filterable column.
        Archived exercises are excluded so the UI only shows actionable options.
        """
        def _distinct(column):
            rows = (
                db.query(column)
                .filter(Exercise.is_archived.is_(False))
                .filter(column.isnot(None))
                .distinct()
                .order_by(column)
                .all()
            )
            return [r[0] for r in rows if r[0] and r[0].strip()]

        return FilterOptions(
            exercise_types=_distinct(Exercise.exercise_type),
            muscle_groups=_distinct(Exercise.muscle_group),
            equipment_categories=_distinct(Exercise.equipment_category),
            manual_tags=_distinct(Exercise.manual_tag),
        )

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
        hundred_percent_bodyweight: Optional[bool] = None,
        is_custom: Optional[bool] = None,
        user_id: Optional[uuid.UUID] = None,   # when set, auto-filter by health profile
        include_archived: bool = False,
    ) -> PaginatedExercises:
        """
        Return a paginated, optionally filtered list of exercises.

        Filter priority:
          1. Explicit query params (single exact-match) always take precedence
          2. If use_profile=True and a param is not set, goal defaults (list/IN) fill in
          3. search and boolean filters always stack on top regardless
        """
        # ── Derive goal-based list filters from health profile ──
        goal_exercise_types: Optional[list] = None
        goal_muscle_groups: Optional[list] = None
        goal_equipment_categories: Optional[list] = None

        if user_id:
            profile = (
                db.query(HealthProfile)
                .filter(HealthProfile.user_id == user_id)
                .first()
            )
            if profile and profile.primary_goal:
                defaults = _GOAL_FILTERS.get(profile.primary_goal, {})
                # Only apply goal defaults when the caller hasn't set that filter
                if exercise_type is None:
                    goal_exercise_types = defaults.get("exercise_types")
                if muscle_group is None:
                    goal_muscle_groups = defaults.get("muscle_groups")
                if equipment_category is None:
                    goal_equipment_categories = defaults.get("equipment_categories")

        # ── Build query ──
        q = db.query(Exercise)

        if not include_archived:
            q = q.filter(Exercise.is_archived.is_(False))

        # exercise_type: explicit exact match wins, else goal IN() list
        if exercise_type:
            q = q.filter(Exercise.exercise_type == exercise_type)
        elif goal_exercise_types:
            q = q.filter(Exercise.exercise_type.in_(goal_exercise_types))

        # muscle_group: explicit exact match wins, else goal IN() list
        if muscle_group:
            q = q.filter(Exercise.muscle_group == muscle_group)
        elif goal_muscle_groups:
            q = q.filter(Exercise.muscle_group.in_(goal_muscle_groups))

        # equipment_category: explicit exact match wins, else goal IN() list
        if equipment_category:
            q = q.filter(Exercise.equipment_category == equipment_category)
        elif goal_equipment_categories:
            q = q.filter(Exercise.equipment_category.in_(goal_equipment_categories))

        if search:
            q = q.filter(Exercise.title.ilike(f"%{search}%"))

        if hundred_percent_bodyweight is not None:
            q = q.filter(Exercise.hundred_percent_bodyweight.is_(hundred_percent_bodyweight))

        if is_custom is not None:
            q = q.filter(Exercise.is_custom.is_(is_custom))

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
