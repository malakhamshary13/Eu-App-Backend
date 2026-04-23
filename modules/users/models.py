
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Numeric, SmallInteger, Integer
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
import uuid
from datetime import datetime
from db.database import Base


class User(Base):
    __tablename__ = "Users"
    __table_args__ = {'schema': 'auth'}

    UserId = Column(UNIQUEIDENTIFIER(as_uuid=True), primary_key=True, default=uuid.uuid4)
    Name = Column(String(120), nullable=False)
    Email = Column(String(254), unique=True, nullable=False)
    PasswordHash = Column(String(512), nullable=False)
    Role = Column(String(20), nullable=False)
    IsActive = Column(Boolean, default=True, nullable=False)
    GoogleAuthId = Column(String(255), nullable=True)
    CreatedAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    UpdatedAt = Column(DateTime, default=datetime.utcnow, nullable=False)


class PasswordReset(Base):
    __tablename__ = "PasswordResets"
    __table_args__ = {'schema': 'auth'}

    ResetId = Column(UNIQUEIDENTIFIER(as_uuid=True), primary_key=True, default=uuid.uuid4)
    UserId = Column(UNIQUEIDENTIFIER(as_uuid=True), ForeignKey('auth.Users.UserId', ondelete='CASCADE'), nullable=False)
    Token = Column(String(512), nullable=False)
    ExpiresAt = Column(DateTime, nullable=False)
    UsedAt = Column(DateTime, nullable=True)
    CreatedAt = Column(DateTime, default=datetime.utcnow, nullable=False)


class HealthProfile(Base):
    __tablename__ = "HealthProfiles"
    __table_args__ = {'schema': 'profile'}

    ProfileId = Column(UNIQUEIDENTIFIER(as_uuid=True), primary_key=True, default=uuid.uuid4)
    UserId = Column(UNIQUEIDENTIFIER(as_uuid=True), ForeignKey('auth.Users.UserId', ondelete='CASCADE'), nullable=False, unique=True)
    Age = Column(SmallInteger, nullable=False)
    Weight = Column(Numeric(5, 2, asdecimal=True), nullable=False)
    Height = Column(Numeric(5, 2, asdecimal=True), nullable=False)
    # BMI is computed in the database, do not insert
    Gender = Column(String(20), nullable=True)
    PrimaryGoal = Column(String(30), nullable=False)
    FitnessLevel = Column(String(20), nullable=False, default='Beginner')
    ActivityLevel = Column(String(30), nullable=False, default='Sedentary')
    DailyCalorieTarget = Column(Integer, nullable=True)
    CurrentStreak = Column(Integer, nullable=False, default=0)
    LongestStreak = Column(Integer, nullable=False, default=0)
    InjuryDetails = Column(String(500), nullable=True)
    RecoveryStage = Column(String(100), nullable=True)
    MedicalDietNotes = Column(String(1000), nullable=True)
    CreatedAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    UpdatedAt = Column(DateTime, default=datetime.utcnow, nullable=False)