from sqlalchemy.orm import Session
from modules.workouts.models import Workout


class WorkoutRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_goal(self, goal: str):
        return self.db.query(Workout).filter(Workout.goal == goal).all()