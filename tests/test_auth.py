import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from modules.users.service import AuthService
from modules.users.schemas import UserCreate

# Valid payload
USER_DATA = {
    "Full_name": "Test User",
    "username": "testuser",
    "email": "test@example.com",
    "password": "SecurePassword123!"
}


@patch("modules.users.service.supabase")
@patch("modules.users.service._repo")
def test_tc_u01_reject_duplicate_username(mock_repo, mock_supabase):
    service = AuthService()
    user_create = UserCreate(**USER_DATA)
    mock_db = MagicMock()

    # ✅ Proper Supabase mock
    mock_supabase.auth.sign_up.return_value = MagicMock(
        session=MagicMock(access_token="mock_token", refresh_token="mock_refresh"),
        user=MagicMock(
            id="user-123",
            email="test@example.com",
            user_metadata={}
        )
    )

    # ✅ Trigger DB failure
    mock_repo.create_profile_user.side_effect = IntegrityError(
        statement="",
        params={},
        orig=Exception("duplicate username")
    )

    with pytest.raises(HTTPException) as exc:
        service.register_user(mock_db, user_create)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Username already exists"


@patch("modules.users.service.supabase")
@patch("modules.users.service._repo")
def test_tc_u02_reject_duplicate_email(mock_repo, mock_supabase):
    service = AuthService()
    user_create = UserCreate(**USER_DATA)
    mock_db = MagicMock()

    # ✅ Supabase fails BEFORE DB
    mock_supabase.auth.sign_up.side_effect = Exception("User already registered")

    with pytest.raises(HTTPException) as exc:
        service.register_user(mock_db, user_create)

    # ✅ Ensure DB never called
    mock_repo.create_profile_user.assert_not_called()

    assert exc.value.status_code == 400
    assert exc.value.detail == "Email already exists"


def test_tc_u03_reject_invalid_password():
    service = AuthService()
    mock_db = MagicMock()

    # Too short
    user_data = USER_DATA.copy()
    user_data["password"] = "abc"
    user_create = UserCreate(**user_data)

    with pytest.raises(HTTPException) as exc:
        service.register_user(mock_db, user_create)

    assert exc.value.status_code == 400

    # Too long
    user_data["password"] = "A" * 73
    user_create = UserCreate(**user_data)

    with pytest.raises(HTTPException) as exc:
        service.register_user(mock_db, user_create)

    assert exc.value.status_code == 400