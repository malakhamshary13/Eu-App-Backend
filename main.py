from fastapi import FastAPI
from modules.users.router import router as auth_router
from modules.exercises.router import router as exercises_router
from modules.workouts.router import router as workouts_router
from modules.meals.router import router as meals_router
from modules.meal_plans.router import router as meal_plans_router
from fastapi.middleware.cors import CORSMiddleware

# Tables are managed by Supabase migrations — we do NOT call create_all here.
# SQLAlchemy is used only as a query layer over existing Supabase tables.

app = FastAPI(
    title="EU App Backend API",
    description="Fitness & nutrition backend powered by Supabase",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



app.include_router(auth_router)
app.include_router(exercises_router)
app.include_router(workouts_router)
app.include_router(meals_router)
app.include_router(meal_plans_router)

@app.get("/")
def root():
    return {"message": "EU APP  is steady and ready to serve! (KEMO is here to help you with your fitness journey)"}