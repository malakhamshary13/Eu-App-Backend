from fastapi import FastAPI
from db.database import Base, engine
from modules.users.router import router as auth_router
from modules.exercises.router import router as exercises_router
from modules.users import models
from modules.exercises import models as exercise_models
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(title="EU App Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
Base.metadata.create_all(bind=engine)


app.include_router(auth_router)
app.include_router(exercises_router)

@app.get("/")
def root():
    return {"message": "API is running"}