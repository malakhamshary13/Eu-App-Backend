from sqlalchemy.orm import Session
from modules.meals.models import Meal


class MealRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_goal(self, goal: str):
        return self.db.query(Meal).filter(Meal.goal == goal).all()