import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import HTTPException
from modules.users.service import AuthService

def setup_mock_db():
    mock_db = MagicMock()
    # Mock the ProfileUser query for admin/user role printing logic in login_user
    mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(role="general")
    return mock_db

@patch("modules.users.service.supabase")
@patch("modules.users.service._repo")
def test_tc_u07_login_with_email(mock_repo, mock_supabase):
    """
    TC-U07: Login with Email
    """
    service = AuthService()
    mock_db = setup_mock_db()

    # Mock Supabase to succeed
    mock_supabase.auth.sign_in_with_password.return_value = MagicMock(
        session=MagicMock(access_token="mock_access", refresh_token="mock_refresh"),
        user=MagicMock(id="123", email="test@example.com", user_metadata={"full_name": "Test User"})
    )

    token = service.login_user(mock_db, "test@example.com", "securepass")

    # 1. Ensure it passed the exact email to Supabase
    mock_supabase.auth.sign_in_with_password.assert_called_once_with(
        {"email": "test@example.com", "password": "securepass"}
    )
    # 2. Ensure it never tried to look up a username
    mock_repo.get_email_by_username.assert_not_called()
    # 3. Ensure a valid token object is returned
    assert token.access_token == "mock_access"
    assert token.user.email == "test@example.com"


@patch("modules.users.service.supabase")
@patch("modules.users.service._repo")
def test_tc_u08_login_with_username(mock_repo, mock_supabase):
    """
    TC-U08: Login with Username
    """
    service = AuthService()
    mock_db = setup_mock_db()

    # Mock the database returning an email for the provided username
    mock_repo.get_email_by_username.return_value = "resolved@example.com"

    # Mock Supabase to succeed
    mock_supabase.auth.sign_in_with_password.return_value = MagicMock(
        session=MagicMock(access_token="mock_access", refresh_token="mock_refresh"),
        user=MagicMock(id="123", email="resolved@example.com", user_metadata={"full_name": "Test User"})
    )

    token = service.login_user(mock_db, "testuser", "securepass")

    # 1. Ensure the DB lookup was triggered
    mock_repo.get_email_by_username.assert_called_once_with(mock_db, "testuser")
    # 2. Ensure it passed the RESOLVED email to Supabase, not the username
    mock_supabase.auth.sign_in_with_password.assert_called_once_with(
        {"email": "resolved@example.com", "password": "securepass"}
    )
    assert token.access_token == "mock_access"


@patch("modules.users.service.supabase")
@patch("modules.users.service._repo")
def test_tc_u09_invalid_username(mock_repo, mock_supabase):
    """
    TC-U09: Invalid Username (username does not exist in the database)
    """
    service = AuthService()
    mock_db = setup_mock_db()

    # Mock the database saying "I couldn't find an email for that username"
    mock_repo.get_email_by_username.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        service.login_user(mock_db, "nonexistentuser", "securepass")

    # Ensure it threw a 401 Unauthorized
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid username or password."
    # Ensure Supabase was NEVER called because we failed early
    mock_supabase.auth.sign_in_with_password.assert_not_called()


@patch("modules.users.service.supabase")
@patch("modules.users.service._repo")
def test_tc_u10_invalid_password(mock_repo, mock_supabase):
    """
    TC-U10: Invalid Password (Supabase rejects the credentials)
    """
    service = AuthService()
    mock_db = setup_mock_db()

    # Mock Supabase throwing an exception for wrong password
    mock_supabase.auth.sign_in_with_password.side_effect = Exception("Invalid login credentials")

    with pytest.raises(HTTPException) as exc_info:
        service.login_user(mock_db, "test@example.com", "wrongpassword")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid credentials."


@patch("modules.users.service.supabase")
@patch("modules.users.service._repo")
def test_tc_u11_missing_session(mock_repo, mock_supabase):
    """
    TC-U11: Supabase returns a user but no session
    """
    service = AuthService()
    mock_db = setup_mock_db()

    # Mock Supabase returning no session (e.g., if email confirmation is required but incomplete)
    mock_supabase.auth.sign_in_with_password.return_value = MagicMock(
        session=None,
        user=MagicMock(id="123")
    )

    with pytest.raises(HTTPException) as exc_info:
        service.login_user(mock_db, "test@example.com", "securepass")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Authentication failed. No session returned."
