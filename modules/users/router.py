import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from modules.users.repository import AuthRepository
from modules.users.schemas import UserCreate, Token, UserLogin, UserMetricInput
from modules.users.service import AuthService
from modules.users.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])
service = AuthService()
repo = AuthRepository()  # Access the repository for direct queries in routes

@router.post("/register", response_model=Token)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    return service.register_user(db, user_data)

@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    return service.login_user(db, user_data.username, user_data.password)

@router.post("/user-metrics")
def store_user_metrics(
    data:  UserMetricInput,
    user_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    return service.store_user_metrics(db, user_id, data)

@router.get("/user-metrics")
def get_user_metrics(
    user_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    return repo.get_health_profile_by_user_id(db, user_id)