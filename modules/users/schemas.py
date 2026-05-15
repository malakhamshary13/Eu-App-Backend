from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal

import uuid

from db.database import ORMBaseModel


# ──────────────────────────────────────────
# Request Schemas
# ──────────────────────────────────────────

class UserCreate(BaseModel):
    """Payload for POST /auth/register"""
    Full_name: str
    username: str       # unique display handle
    email: EmailStr
    password: str
    


class UserLogin(BaseModel):
    """Payload for POST /auth/login.
    'login_identifier' can be either an email address or a username.
    """
    login_identifier: str   # email OR username
    password: str


class RefreshTokenRequest(BaseModel):
    """Payload for POST /auth/refresh."""
    refresh_token: str


class UserMetricInput(BaseModel):
    """Payload for POST /auth/user-metrics.
    All constraints mirror the DB CHECK constraints on profile.health_profiles.
    """
    age:            int   = Field(..., ge=5,   le=100,  description="Age in years (5–100).")
    weight:         float = Field(..., ge=20,  le=300,  description="Weight in kg (20–300).")
    height:         float = Field(..., ge=50,  le=280,  description="Height in cm (50–280).")
    gender:         Literal["male", "female"]           # NOT NULL in DB — required
    primary_goal:   Literal["weight_loss", "muscle_gain", "rehab", "general"] = "general"
    fitness_level:  Literal["Beginner", "Intermediate", "Advanced"] = "Beginner"
    activity_level: Literal[
        "Sedentary",
        "Lightly Active",
        "Moderately Active",
        "Very Active",
        "Extra Active",
    ] = "Sedentary"
    daily_calorie_target: Optional[int]   = Field(None, ge=500, le=10000, description="Target kcal/day (500‚Äì10 000).")
    injury_details:       Optional[str]  = None
    recovery_stage:       Optional[Literal["acute", "sub-acute", "chronic"]] = None
    medical_diet_notes:   Optional[str]  = None


# ──────────────────────────────────────────
# Response Schemas
# ──────────────────────────────────────────

class UserInfo(BaseModel):
    """Slim user info embedded in Token responses."""
    id: str
    email: str
    name: Optional[str] = None


class Token(BaseModel):
    """JWT token pair returned after login / register."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: UserInfo


class UserListItem(ORMBaseModel):
    """A single user row returned by the admin GET /auth/users endpoint."""
    id: uuid.UUID
    full_name: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    role: str
    is_active: bool


class HealthProfileResponse(ORMBaseModel):
    """Response schema for health profile endpoints."""
    user_id: uuid.UUID
    age: int
    weight: float
    height: float
    gender: Optional[Literal["male", "female"]] = None
    primary_goal: str
    fitness_level: str
    activity_level: str
    daily_calorie_target: Optional[int] = None
    current_streak: int = 0
    longest_streak: int = 0
    injury_details: Optional[str] = None
    recovery_stage: Optional[str] = None
    medical_diet_notes: Optional[str] = None
