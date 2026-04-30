import uuid
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.auth import get_current_user, require_admin
from db.database import get_db
from modules.users.repository import AuthRepository
from modules.users.schemas import (
    UserCreate, Token, UserLogin, UserMetricInput,
    UserListItem, HealthProfileResponse, RefreshTokenRequest,
)
from modules.users.service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])
service = AuthService()
repo = AuthRepository()


# ──────────────────────────────────────────
# Public endpoints  (no token required)
# ──────────────────────────────────────────

@router.post("/register", response_model=Token, summary="Register a new user")
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new account with Supabase Auth.
    Returns a JWT access token + refresh token on success.
    """
    return service.register_user(db, user_data)


@router.post("/login", response_model=Token, summary="Login with email or username & password")
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate with either an email address or a username, plus password.
    Returns a JWT access token + refresh token on success.
    """
    return service.login_user(db, user_data.login_identifier, user_data.password)


@router.post("/refresh", response_model=Token, summary="Refresh access token")
def refresh(body: RefreshTokenRequest):
    """
    Exchange a valid refresh_token for a fresh access_token + rotated refresh_token.
    The old refresh_token is immediately invalidated by Supabase after use.
    No Bearer header needed — just send the refresh_token in the request body.
    """
    return service.refresh_session(body.refresh_token)


# ──────────────────────────────────────────
# Protected endpoints  (Bearer token required)
# ──────────────────────────────────────────

@router.get("/me", summary="Get current authenticated user")
def me(current_user=Depends(get_current_user)):
    """
    Returns the Supabase user object for the bearer token supplied.
    Useful for client-side session hydration.
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": (current_user.user_metadata or {}).get("username"),
    }


@router.post(
    "/health-profile",
    response_model=HealthProfileResponse,
    summary="Create or update health profile",
)
def create_health_profile(
    data: UserMetricInput,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create or update the authenticated user's health profile.
    user_id is derived from the JWT — no need to pass it manually.
    The profile uses the user's ID as its primary key (one profile per user).
    """
    user_id = uuid.UUID(str(current_user.id))
    return service.store_user_metrics(db, user_id, data)


@router.get("/health-profile",response_model=HealthProfileResponse,summary="Get my health profile")
def get_health_profile(current_user=Depends(get_current_user),db: Session = Depends(get_db)):
    """
    Return the authenticated user's stored health profile.
    """
    user_id = uuid.UUID(str(current_user.id))
    return repo.get_health_profile_by_user_id(db, user_id)


# ──────────────────────────────────────────
# Admin-only endpoints
# ──────────────────────────────────────────

@router.get(
    "/users",
    response_model=List[UserListItem],
    summary="[Admin] List all registered users",
)
def list_users(
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Returns all users from profile.users.
    Requires role='admin' in profile.users.
    Admins are created manually — not through /register.
    """
    return repo.get_all_users(db)