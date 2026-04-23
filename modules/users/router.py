from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from modules.users.schemas import UserCreate, Token,UserLogin
from modules.users.service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])
service = AuthService()

@router.post("/register", response_model=Token)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    return service.register_user(db, user_data)

@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    return service.login_user(db, user_data.username, user_data.password)