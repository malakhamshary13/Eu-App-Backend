import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from db.database import supabase, get_db

# Bearer token extractor — looks for "Authorization: Bearer <token>"
_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
):
    """
    FastAPI dependency that validates a Supabase JWT and returns the
    authenticated user object.

    Usage in a route:
        @router.get("/me")
        def me(current_user = Depends(get_current_user)):
            return {"id": current_user.id, "email": current_user.email}
    """
    token = credentials.credentials
    try:
        response = supabase.auth.get_user(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not response or not response.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return response.user


async def require_admin(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    FastAPI dependency that ensures the caller is an admin.
    Reads the role from profile.users (our extension table).
    Raises 403 Forbidden if the user's role is not 'admin'.

    Usage in a route:
        @router.get("/users")
        def list_users(admin=Depends(require_admin)):
            ...
    """
    from modules.users.models import ProfileUser  # local import avoids circular

    user_id = uuid.UUID(str(current_user.id))
    profile = db.query(ProfileUser).filter(ProfileUser.id == user_id).first()

    if not profile or profile.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required.",
        )

    return current_user

# for checking if the user is admin
# FastAPI sees this and runs the full chain before your function even executes:
# 1. extract bearer token
# 2. validate JWT
# 3. query profile.users
# 4. check role
# 5. only then call your endpoint handler

"""
HTTP Request arrives with:
  Authorization: Bearer eyJhbGci...

        │
        ▼
┌─────────────────────────────────────┐
│  HTTPBearer()  (in core/auth.py)    │
│  Extracts the raw token string      │
│  from the Authorization header      │
└─────────────────────────────────────┘
        │  credentials.credentials = "eyJhbGci..."
        ▼
┌─────────────────────────────────────┐
│  get_current_user()                 │
│  Calls supabase.auth.get_user(token)│
│  Returns the Supabase user object   │
└─────────────────────────────────────┘
        │  current_user = { id, email, ... }
        ▼
┌─────────────────────────────────────┐
│  require_admin()                    │
│  Queries profile.users WHERE        │
│  id = current_user.id               │
│  Checks role == 'admin'             │
│  → 403 if not admin                 │
│  → returns current_user if admin    │
└─────────────────────────────────────┘
        │  _admin = current_user  (admin verified)
        ▼
┌─────────────────────────────────────┐
│  create_exercise()  runs            │
└─────────────────────────────────────┘
"""
