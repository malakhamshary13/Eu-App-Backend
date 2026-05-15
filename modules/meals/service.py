import uuid
from sqlalchemy.orm import Session
from modules.meals.repository import MealRepository
from modules.meals.schemas import MealCreate

_repo = MealRepository()


class MealService:

    def get_filter_options(self, db: Session):
        return _repo.get_filter_options(db)

    def list_meals(self, db: Session, **kwargs):
        return _repo.get_meals(db, **kwargs)

    def get_meal(self, db: Session, meal_id: uuid.UUID):
        return _repo.get_meal_by_id(db, meal_id)

    def recommend_meals(self, db: Session, user_id: uuid.UUID, page: int, page_size: int):
        return _repo.recommend_meals(db, user_id, page=page, page_size=page_size)

    def create_meal(self, db: Session, data: MealCreate):
        return _repo.create_meal(db, data)

    def delete_meal(self, db: Session, meal_id: uuid.UUID):
        return _repo.delete_meal(db, meal_id)
