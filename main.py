from fastapi import FastAPI
from db.database import Base, engine
from modules.workouts.router import router as auth_router
from modules.workouts import models  # important so SQLAlchemy sees User model

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Workout API with Auth")

app.include_router(auth_router)

@app.get("/")
def root():
    return {"message": "API is running"}