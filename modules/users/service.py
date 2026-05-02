import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from db.database import supabase
from modules.users.schemas import UserCreate, Token, UserInfo, UserMetricInput, RefreshTokenRequest
from modules.users.repository import AuthRepository
from modules.users.models import ProfileUser

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
                detail="Email already exists",
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


# user=User(id='2c445212-b3e5-45ed-8b01-4bd5819546ef', app_metadata={'provider': 'email', 'providers': ['email']}, user_metadata={'email_verified': True}, aud='authenticated', confirmation_sent_at=None, recovery_sent_at=None, email_change_sent_at=None, new_email=None, new_phone=None, invited_at=None, action_link=None, email='karim2282004@gmail.com', phone='', created_at=datetime.datetime(2026, 4, 30, 19, 21, 59, 932554, tzinfo=TzInfo(0)), confirmed_at=datetime.datetime(2026, 4, 30, 19, 21, 59, 953124, tzinfo=TzInfo(0)), email_confirmed_at=datetime.datetime(2026, 4, 30, 19, 21, 59, 953124, tzinfo=TzInfo(0)), phone_confirmed_at=None, last_sign_in_at=datetime.datetime(2026, 5, 1, 6, 14, 39, 402672, tzinfo=TzInfo(0)), role='authenticated', updated_at=datetime.datetime(2026, 5, 1, 6, 14, 39, 423236, tzinfo=TzInfo(0)), identities=[UserIdentity(id='2c445212-b3e5-45ed-8b01-4bd5819546ef', identity_id='465e85e1-fc59-4dab-8a22-73fe91555509', user_id='2c445212-b3e5-45ed-8b01-4bd5819546ef', identity_data={'email': 'karim2282004@gmail.com', 'email_verified': False, 'phone_verified': False, 'sub': '2c445212-b3e5-45ed-8b01-4bd5819546ef'}, provider='email', created_at=datetime.datetime(2026, 4, 30, 19, 21, 59, 949500, tzinfo=TzInfo(0)), last_sign_in_at=datetime.datetime(2026, 4, 30, 19, 21, 59, 949377, tzinfo=TzInfo(0)), updated_at=datetime.datetime(2026, 4, 30, 19, 21, 59, 949500, tzinfo=TzInfo(0)))], is_anonymous=False, is_sso_user=False, factors=None, deleted_at=None, banned_until=None) session=Session(provider_token=None, provider_refresh_token=None, access_token='eyJhbGciOiJFUzI1NiIsImtpZCI6IjZhODBhZTNkLTVhZWEtNDUwYS05ODA0LWFlMzE1MmI1NDJmZSIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL293c3F1c2xiYXNuZXVvZ3FndmNjLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiIyYzQ0NTIxMi1iM2U1LTQ1ZWQtOGIwMS00YmQ1ODE5NTQ2ZWYiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzc3NjE5Njc5LCJpYXQiOjE3Nzc2MTYwNzksImVtYWlsIjoia2FyaW0yMjgyMDA0QGdtYWlsLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWxfdmVyaWZpZWQiOnRydWV9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzc3NjE2MDc5fV0sInNlc3Npb25faWQiOiI1N2ViYmRlYS03NDc1LTQ5NTAtOTUzMi1kMzVmNWM4MzMwMGMiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.BDv74nZ6tpplA9kcyS4A714SNm-Zu8aWI6OiJOyvU7Skx2SQwycGMJIpSr4ZCS6gonvE59-sKj_MG4WDzo5xCw', refresh_token='b7xjw552cs4l', expires_in=3600, expires_at=1777619679, token_type='bearer', user=User(id='2c445212-b3e5-45ed-8b01-4bd5819546ef', app_metadata={'provider': 'email', 'providers': ['email']}, user_metadata={'email_verified': True}, aud='authenticated', confirmation_sent_at=None, recovery_sent_at=None, email_change_sent_at=None, new_email=None, new_phone=None, invited_at=None, action_link=None, email='karim2282004@gmail.com', phone='', created_at=datetime.datetime(2026, 4, 30, 19, 21, 59, 932554, tzinfo=TzInfo(0)), confirmed_at=datetime.datetime(2026, 4, 30, 19, 21, 59, 953124, tzinfo=TzInfo(0)), email_confirmed_at=datetime.datetime(2026, 4, 30, 19, 21, 59, 953124, tzinfo=TzInfo(0)), phone_confirmed_at=None, last_sign_in_at=datetime.datetime(2026, 5, 1, 6, 14, 39, 402672, tzinfo=TzInfo(0)), role='authenticated', updated_at=datetime.datetime(2026, 5, 1, 6, 14, 39, 423236, tzinfo=TzInfo(0)), identities=[UserIdentity(id='2c445212-b3e5-45ed-8b01-4bd5819546ef', identity_id='465e85e1-fc59-4dab-8a22-73fe91555509', user_id='2c445212-b3e5-45ed-8b01-4bd5819546ef', identity_data={'email': 'karim2282004@gmail.com', 'email_verified': False, 'phone_verified': False, 'sub': '2c445212-b3e5-45ed-8b01-4bd5819546ef'}, provider='email', created_at=datetime.datetime(2026, 4, 30, 19, 21, 59, 949500, tzinfo=TzInfo(0)), last_sign_in_at=datetime.datetime(2026, 4, 30, 19, 21, 59, 949377, tzinfo=TzInfo(0)), updated_at=datetime.datetime(2026, 4, 30, 19, 21, 59, 949500, tzinfo=TzInfo(0)))], is_anonymous=False, is_sso_user=False, factors=None, deleted_at=None, banned_until=None))

        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if response.user.id : 
            profile_user=db.query(ProfileUser).filter(ProfileUser.id == response.user.id).first()
            if profile_user:
                role = profile_user.role
                if role== "admin": print("This is admin")
                else: print("This is user")
                    
        

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
