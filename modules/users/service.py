from datetime import timedelta
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.config import settings
from core.security import hash_password, verify_password, create_access_token
from modules.users.repository import AuthRepository
from modules.users.schemas import UserCreate, UserMetricInput


class AuthService:
    def __init__(self):
        self.repo = AuthRepository()

    def register_user(self, db: Session, user_data: UserCreate):
        existing_username = self.repo.get_user_by_username(db, user_data.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )

        existing_email = self.repo.get_user_by_email(db, user_data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )

        if len(user_data.password.encode("utf-8")) > 72:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must not exceed 72 bytes for bcrypt hashing"
            )

        hashed_pw = hash_password(user_data.password)

        user = self.repo.create_user(
            db=db,
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_pw,
            role=user_data.role,
            is_active=user_data.is_active,
            google_auth_id=user_data.google_auth_id
        )

        access_token = create_access_token(
            data={"sub": user.Name},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        # id = db.query(user.Id).filter(user.Name == user_data.username).first()[0]
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": str(user.UserId)
        }

    def login_user(self, db: Session, username: str, password: str):
        if len(password.encode("utf-8")) > 72:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must not exceed 72 bytes for bcrypt verification"
            )

        user = self.repo.get_user_by_username(db, username)
        if not user or not verify_password(password, user.PasswordHash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        access_token = create_access_token(
            data={"sub": user.Name},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": str(user.UserId)
        }
    # Map snake_case schema fields → PascalCase model columns
    _METRIC_FIELD_MAP = {
        "weight": "Weight",
        "height": "Height",
        "age": "Age",
        "gender": "Gender",
        "primary_goal": "PrimaryGoal",
        "fitness_level": "FitnessLevel",
        "activity_level": "ActivityLevel",
        "daily_calorie_target": "DailyCalorieTarget",
        "injury_details": "InjuryDetails",
        "recovery_stage": "RecoveryStage",
        "medical_diet_notes": "MedicalDietNotes",
    }

    def store_user_metrics(self, db: Session, user_id, data: UserMetricInput):
        existing_profile = self.repo.get_health_profile_by_user_id(db, user_id)
        raw = data.dict(exclude_unset=True)

        profile_data = {}
        for k, v in raw.items():
            if k in ("weight", "height") and not isinstance(v, Decimal):
                profile_data[self._METRIC_FIELD_MAP[k]] = Decimal(str(v))
            else:
                profile_data[self._METRIC_FIELD_MAP[k]] = v

        if existing_profile:
            return self.repo.update_health_profile(db, existing_profile, profile_data)
        else:
            return self.repo.create_health_profile(db, user_id, profile_data)
            return self.repo.create_health_profile(db, user_id, profile_data)