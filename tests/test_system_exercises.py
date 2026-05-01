import pytest
import sys
import os
import uuid
from fastapi.testclient import TestClient

# Add parent directory to path so 'main' can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from db.database import SessionLocal
from modules.users.models import ProfileUser

# Use TestClient with the actual FastAPI app
client = TestClient(app)

def test_tc_s05_complete_exercise_lifecycle():
    """
    TC-S05: Complete Exercise Lifecycle
    Register a user, manually elevate them to 'admin' in the test database,
    and verify they can Create, Read, and Delete an exercise via the API.
    """
    unique_id = str(uuid.uuid4())[:8]
    test_email = f"systemtest_exer_{unique_id}@example.com"
    test_username = f"sysuser_exer_{unique_id}"
    real_password = "SecurePassword123!"

    register_payload = {
        "Full_name": f"Exercise Test {unique_id}",
        "username": test_username,
        "email": test_email,
        "password": real_password
    }

    # 1. Register a standard user
    reg_response = client.post("/auth/register", json=register_payload)
    assert reg_response.status_code in [200, 201], "Setup failed: Could not register user"
    
    token = reg_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Extract user ID from /auth/me
    me_response = client.get("/auth/me", headers=headers)
    assert me_response.status_code == 200
    user_id = me_response.json()["id"]

    # 3. Elevate user to admin directly in the database to bypass manual admin creation
    db = SessionLocal()
    try:
        profile = db.query(ProfileUser).filter(ProfileUser.id == user_id).first()
        assert profile is not None, "Profile row was not created"
        profile.role = "admin"
        db.commit()
    finally:
        db.close()

    # =========================================================
    # Step 4: Create Exercise
    # =========================================================
    exercise_payload = {
        "title": f"System Test Pushups {unique_id}",
        "description": "Standard pushups for system testing",
        "muscle_group": "Chest",
        "equipment": "Bodyweight",
        "difficulty": "Beginner",
        "video_url": "https://example.com/pushups.mp4"
    }

    create_response = client.post("/exercises/", json=exercise_payload, headers=headers)
    assert create_response.status_code in [200, 201], f"Failed to create exercise: {create_response.text}"
    
    created_exercise = create_response.json()
    exercise_id = created_exercise["id"]
    assert created_exercise["title"] == exercise_payload["title"]

    # =========================================================
    # Step 5: Read Exercise
    # =========================================================
    get_response = client.get(f"/exercises/{exercise_id}", headers=headers)
    assert get_response.status_code == 200, "Failed to fetch created exercise"
    assert get_response.json()["id"] == exercise_id

    # =========================================================
    # Step 6: Delete Exercise
    # =========================================================
    delete_response = client.delete(f"/exercises/{exercise_id}", headers=headers)
    # The endpoint might return 200 or 204 depending on implementation, assume 200 based on standard FastAPI defaults unless specified
    assert delete_response.status_code in [200, 204], f"Failed to delete exercise: {delete_response.text}"

    # Verify it is actually gone from the public listings (since it is soft-deleted)
    verify_deleted = client.get(f"/exercises/?search={unique_id}", headers=headers)
    assert verify_deleted.status_code == 200
    assert verify_deleted.json()["total"] == 0, "Exercise still appears in listings after being archived"

