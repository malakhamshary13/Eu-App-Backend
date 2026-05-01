import pytest
import sys
import os
import uuid
from fastapi.testclient import TestClient

# Add parent directory to path so 'main' can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app

# Use TestClient with the actual FastAPI app
client = TestClient(app)

def test_tc_s03_admin_endpoint_restriction():
    """
    TC-S03: Admin Endpoint Restriction
    Register a standard user (role='general') and attempt to call an admin-only endpoint.
    Verify that the `require_admin` dependency blocks it with a 403 Forbidden error.
    """
    unique_id = str(uuid.uuid4())[:8]
    test_email = f"systemtest_rbac_{unique_id}@example.com"
    test_username = f"sysuser_rbac_{unique_id}"
    real_password = "SecurePassword123!"

    register_payload = {
        "Full_name": f"RBAC Test {unique_id}",
        "username": test_username,
        "email": test_email,
        "password": real_password
    }

    # 1. Register a standard user
    reg_response = client.post("/auth/register", json=register_payload)
    assert reg_response.status_code in [200, 201], "Setup failed: Could not register user"
    
    token = reg_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Attempt to access the Admin-only /auth/users endpoint
    admin_response = client.get("/auth/users", headers=headers)
    
    # 3. Verify it is blocked with 403 Forbidden
    assert admin_response.status_code == 403, f"Expected 403 Forbidden, got {admin_response.status_code}"
    
    error_data = admin_response.json()
    assert error_data["detail"] == "Access denied. Admin role required."


