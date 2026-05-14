from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from core.limiter import limiter
from modules.users.router import router as auth_router
from modules.exercises.router import router as exercises_router
from modules.workouts.router import router as workouts_router
from modules.meals.router import router as meals_router
from modules.meal_plans.router import router as meal_plans_router
from modules.meal_tracking.router import router as meal_tracking_router
from fastapi.middleware.cors import CORSMiddleware

# Tables are managed by Supabase migrations — we do NOT call create_all here.
# SQLAlchemy is used only as a query layer over existing Supabase tables.

app = FastAPI(
    title="EU App Backend API",
    description="Fitness & nutrition backend powered by Supabase",
    version="1.0.0",
)

# Rate-limit wiring 
# Attach the shared limiter to app.state so slowapi can reach it from decorators,
# then register the built-in 429 handler so exceeded limits return proper JSON.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
app.include_router(meal_tracking_router)


@app.get("/")
def root():
    return {"message": "EU APP  is steady and ready to serve! (KEMO is here to help you with your fitness journey)"}
