from sqlalchemy.orm import Session
from modules.users.models import User

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
            role: str = "user",
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