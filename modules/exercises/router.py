from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from modules.exercises.schemas import ExerciseOut
from modules.exercises.service import ExerciseService

router = APIRouter(prefix="/exercises", tags=["Exercises"])
service = ExerciseService()


@router.get("/", response_model=List[ExerciseOut])
def get_exercises(
    count: int = Query(..., gt=0, le=500, description="Number of exercises to return"),
    db: Session = Depends(get_db),
):
    """Return *count* exercises from the library, ordered by priority."""
    return service.get_exercises(db, count)
