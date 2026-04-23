from fastapi import FastAPI
from db.database import Base, engine

from modules.users.router import router as auth_router
from modules.recommendations.router import router as recommendation_router

# import models before create_all
from modules.users.models import User
from modules.meals.models import Meal
from modules.workouts.models import Workout

Base.metadata.create_all(bind=engine)

app = FastAPI(title="EU App Backend API")

app.include_router(auth_router)
app.include_router(recommendation_router)


@app.get("/")
def root():
    return {"message": "API is running"}