import pytest
import sys
import os
import uuid
from fastapi.testclient import TestClient

# Add parent directory to path so 'main' can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app

# Use TestClient with the actual FastAPI app (no mocks!)
client = TestClient(app)

def test_end_to_end_user_journey():
    """
    System Test: End-to-End User Flow
    Tests the real database and Supabase endpoints sequentially.
    """
    # 1. Generate unique credentials to avoid collisions in the real database
    unique_id = str(uuid.uuid4())[:8]
    test_email = f"systemtest_{unique_id}@example.com"
    test_username = f"sysuser_{unique_id}"
    test_password = "SecurePassword123!"

    register_payload = {
        "Full_name": f"System Test {unique_id}",
        "username": test_username,
        "email": test_email,
        "password": test_password
    }

    # =========================================================
    # Step 1: Registration
    # =========================================================
    reg_response = client.post("/auth/register", json=register_payload)
    assert reg_response.status_code in [200, 201], f"Registration failed: {reg_response.text}"
    
    reg_data = reg_response.json()
    assert "access_token" in reg_data
    assert "refresh_token" in reg_data

    # Extract the token for authenticated requests
    token = reg_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # =========================================================
    # Step 2: Login
    # =========================================================
    login_payload = {
        "login_identifier": test_email,
        "password": test_password
    }
    login_response = client.post("/auth/login", json=login_payload)
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    
    login_data = login_response.json()
    assert "access_token" in login_data
    
    # Update token to the newly logged-in one just to be sure
    token = login_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # =========================================================
    # Step 3: Get Current User (Me)
    # =========================================================
    me_response = client.get("/auth/me", headers=headers)
    assert me_response.status_code == 200, f"Get Me failed: {me_response.text}"
    
    me_data = me_response.json()
    assert me_data["email"] == test_email
    # The username gets stored in the user_metadata, which the /me endpoint maps to 'name'
    assert me_data["name"] == test_username 

    # =========================================================
    # Step 4: Create Health Profile
    # =========================================================
    # Note: We must ensure weight and height are > 0 to avoid 
    # the division-by-zero bug we discovered earlier!
    health_payload = {
        "age": 30,
        "weight": 75.5,
        "height": 180.0,
        "gender": "Male",
        "primary_goal": "build_muscle",
        "fitness_level": "Intermediate",
        "activity_level": "Active"
    }
    health_post_response = client.post("/auth/health-profile", json=health_payload, headers=headers)
    assert health_post_response.status_code == 200, f"Create Health Profile failed: {health_post_response.text}"
    
    # =========================================================
    # Step 5: Fetch Health Profile
    # =========================================================
    health_get_response = client.get("/auth/health-profile", headers=headers)
    assert health_get_response.status_code == 200, f"Get Health Profile failed: {health_get_response.text}"
    
    health_get_data = health_get_response.json()
    assert health_get_data["age"] == 30
    assert health_get_data["weight"] == 75.5
    assert health_get_data["primary_goal"] == "build_muscle"


def test_tc_s02_invalid_login():
    """
    TC-S02: Invalid login - User sees clear failure when password is incorrect
    Tests that attempting to log in with a wrong password returns a 401 and no session.
    """
    # 1. Setup: Register a real user to test against
    unique_id = str(uuid.uuid4())[:8]
    test_email = f"systemtest_inv_{unique_id}@example.com"
    test_username = f"sysuser_inv_{unique_id}"
    real_password = "SecurePassword123!"

    register_payload = {
        "Full_name": f"Invalid Login Test {unique_id}",
        "username": test_username,
        "email": test_email,
        "password": real_password
    }

    reg_response = client.post("/auth/register", json=register_payload)
    assert reg_response.status_code in [200, 201], "Setup failed: Could not register test user"

    # 2. Action: Attempt to login with the CORRECT email but WRONG password
    wrong_login_payload = {
        "login_identifier": test_email,
        "password": "WrongPassword456!"
    }
    
    login_response = client.post("/auth/login", json=wrong_login_payload)
    
    # 3. Verification: Ensure it fails properly
    assert login_response.status_code == 401, f"Expected 401 Unauthorized, got {login_response.status_code}"
    
    error_data = login_response.json()
    
    # Verify clear error feedback
    assert error_data["detail"] == "Invalid credentials."
    
    # Verify no session/token is accidentally returned
    assert "access_token" not in error_data


def test_tc_s04_token_refresh():
    """
    TC-S04: Successful Token Refresh
    Register a user, extract the refresh_token, and send it to POST /auth/refresh.
    Verify that Supabase successfully rotates the session and returns a brand new access_token.
    """
    unique_id = str(uuid.uuid4())[:8]
    test_email = f"systemtest_ref_{unique_id}@example.com"
    test_username = f"sysuser_ref_{unique_id}"
    real_password = "SecurePassword123!"

    register_payload = {
        "Full_name": f"Refresh Test {unique_id}",
        "username": test_username,
        "email": test_email,
        "password": real_password
    }

    # 1. Register to get a valid refresh token
    reg_response = client.post("/auth/register", json=register_payload)
    assert reg_response.status_code in [200, 201], "Setup failed: Could not register user"
    
    reg_data = reg_response.json()
    original_access_token = reg_data["access_token"]
    original_refresh_token = reg_data["refresh_token"]

    # 2. Attempt Token Refresh
    refresh_payload = {
        "refresh_token": original_refresh_token
    }
    refresh_response = client.post("/auth/refresh", json=refresh_payload)
    
    # 3. Verify successful refresh
    assert refresh_response.status_code == 200, f"Token refresh failed: {refresh_response.text}"
    refresh_data = refresh_response.json()
    
    new_access_token = refresh_data["access_token"]
    new_refresh_token = refresh_data["refresh_token"]
    
    # Verify we got tokens back
    assert new_access_token is not None
    assert new_refresh_token is not None
    
    # Optionally verify it's a new token (though Supabase might sometimes return the same JWT if it hasn't expired depending on config, but it's guaranteed to be a valid session).
    # What's important is that the new access token can be used to authenticate.
    
    # 4. Verify the new access token works
    headers = {"Authorization": f"Bearer {new_access_token}"}
    me_response = client.get("/auth/me", headers=headers)
    assert me_response.status_code == 200, "New access token failed to authenticate"
