from sqlalchemy import Column, String, Boolean, DateTime, Integer
from datetime import datetime
from db.database import Base


class User(Base):
    __tablename__ = "users"

    UserId = Column(Integer, primary_key=True, index=True)
    Name = Column(String(120), nullable=False)
    Email = Column(String(254), unique=True, nullable=False)
    PasswordHash = Column(String(512), nullable=False)
    Role = Column(String(20), nullable=False, default="General")
    IsActive = Column(Boolean, default=True, nullable=False)
    GoogleAuthId = Column(String(255), nullable=True)
    CreatedAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    UpdatedAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    goal = Column(String(50), nullable=True)

class PasswordReset(Base):
    __tablename__ = "password_resets"

    ResetId = Column(Integer, primary_key=True, index=True)
    UserId = Column(Integer, nullable=False)
    TokenHash = Column(String(255), nullable=False)
    ExpiresAt = Column(DateTime, nullable=False)
    UsedAt = Column(DateTime, nullable=True)
    CreatedAt = Column(DateTime, default=datetime.utcnow, nullable=False)