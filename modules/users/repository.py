from sqlalchemy.orm import Session
from modules.users.models import User, HealthProfile


class AuthRepository:
    def get_user_by_username(self, db: Session, username: str):
        return db.query(User).filter(User.Name == username).first()

    def get_user_by_email(self, db: Session, email: str):
        return db.query(User).filter(User.Email == email).first()

    def create_user(
            self, db: Session,
            username: str,
            email: str,
            hashed_password: str,
            role: str = "General",
            is_active: bool = True,
            google_auth_id: str | None = None):

        user = User(
            Name=username,
            Email=email,
            PasswordHash=hashed_password,
            Role=role,
            IsActive=is_active,
            GoogleAuthId=google_auth_id
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def get_health_profile_by_user_id(self, db: Session, user_id):
        return db.query(HealthProfile).filter(HealthProfile.UserId == user_id).first()

    def create_health_profile(self, db: Session, user_id, data: dict):
        profile = HealthProfile(UserId=user_id, **data)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    def update_health_profile(self, db: Session, profile: HealthProfile, data: dict):
        for key, value in data.items():
            setattr(profile, key, value)
        db.commit()
        db.refresh(profile)
        return profile