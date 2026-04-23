import random
from sqlalchemy.orm import Session
from modules.meals.repository import MealRepository
from modules.workouts.repository import WorkoutRepository


class RecommendationService:
    def __init__(self, db: Session):
        self.db = db
        self.meal_repo = MealRepository(db)
        self.workout_repo = WorkoutRepository(db)

    def _map_user_goal(self, user_goal: str):
        if user_goal == "lose_weight":
            return "lose_weight", "fat_burn"
        elif user_goal == "gain_muscle":
            return "gain_muscle", "strength"
        else:
            return "maintain", "general_fitness"

    def get_recommendation_for_user(self, user):
        user_goal = user.goal if user.goal else "maintain"
        meal_goal, workout_goal = self._map_user_goal(user_goal)

        meals = self.meal_repo.get_by_goal(meal_goal)
        workouts = self.workout_repo.get_by_goal(workout_goal)

        selected_meal = random.choice(meals) if meals else None
        selected_workout = random.choice(workouts) if workouts else None

        return {
            "meal": selected_meal,
            "workout": selected_workout
        }