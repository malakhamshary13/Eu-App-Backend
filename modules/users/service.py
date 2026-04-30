import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from db.database import supabase
from modules.users.schemas import UserCreate, Token, UserInfo, UserMetricInput, RefreshTokenRequest
from modules.users.repository import AuthRepository

_repo = AuthRepository()


class AuthService:
    """Business logic layer for authentication and user management."""

    # ──────────────────────────────────────────
    # Registration
    # ──────────────────────────────────────────

    def register_user(self, db: Session, user_data: UserCreate) -> Token:
        """
        Register a new user via Supabase Auth.
        - Supabase stores credentials and issues a JWT session.
        - The user's display name and username are saved to profile.users.
        """
        try:
            response = supabase.auth.sign_up(
                {
                    "email": user_data.email,
                    "password": user_data.password,
                    "options": {
                        "data": {
                            "full_name": user_data.Full_name,  # shows in Supabase Auth dashboard
                            "username": user_data.username,
                        }
                    },
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        # Supabase returns session=None when email confirmation is enabled.
        if not response.session:
            # Still persist the profile row so username is reserved.
            if response.user:
                try:
                    _repo.create_profile_user(
                        db,
                        user_id=response.user.id,
                        full_name=user_data.Full_name,
                        username=user_data.username,
                        email=user_data.email,
                    )
                except Exception:
                    pass  # row may already exist from DB trigger
            raise HTTPException(
                status_code=status.HTTP_201_CREATED,
                detail=(
                    "Registration successful. "
                    "Please check your email to confirm your account before logging in."
                ),
            )

        # Persist profile row (username reservation)
        try:
            _repo.create_profile_user(
                db,
                user_id=response.user.id,
                full_name=user_data.Full_name,
                username=user_data.username,
                email=user_data.email,
            )
        except Exception:
            pass  # row may already exist from DB trigger

        return self._build_token(response.user, response.session)

    # ──────────────────────────────────────────
    # Login
    # ──────────────────────────────────────────

    def login_user(self, db: Session, login_identifier: str, password: str) -> Token:
        """
        Authenticate a user via Supabase Auth.
        'login_identifier' can be an email address OR a username.
        If a username is supplied, we resolve it to an email via profile.users first.
        """
        email = login_identifier  # assume email by default

        # Detect if the identifier looks like a username (no '@' symbol)
        if "@" not in login_identifier:
            email = _repo.get_email_by_username(db, login_identifier)
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username or password.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        try:
            response = supabase.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed. No session returned.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return self._build_token(response.user, response.session)

    # ──────────────────────────────────────────
    # Token Refresh
    # ──────────────────────────────────────────

    def refresh_session(self, refresh_token: str) -> Token:
        """
        Exchange a valid refresh_token for a new access_token + rotated refresh_token.
        The old refresh_token is invalidated by Supabase after use.
        """
        try:
            response = supabase.auth.refresh_session(refresh_token)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not refresh session.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return self._build_token(response.user, response.session)

    # ──────────────────────────────────────────
    # Health Profile
    # ──────────────────────────────────────────

    def store_user_metrics(
        self, db: Session, user_id: uuid.UUID, data: UserMetricInput
    ):
        """Create or update the health profile for a given user."""
        return _repo.create_or_update_health_profile(db, user_id, data)

    # ──────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────

    @staticmethod
    def _build_token(user, session) -> Token:
        """Convert a Supabase auth response into our Token schema."""
        name = None
        if user.user_metadata:
            name = user.user_metadata.get("full_name") or user.user_metadata.get("Full_name")

        return Token(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            token_type="bearer",
            user=UserInfo(
                id=str(user.id),
                email=user.email,
                name=name,
            ),
        )
