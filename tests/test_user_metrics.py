import pytest
import sys
import os
import uuid
from unittest.mock import MagicMock
from fastapi import HTTPException
from pydantic import ValidationError

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.users.service import AuthService
from modules.users.schemas import UserMetricInput


def test_tc_u04_reject_invalid_weight():
    """
    TC-U04: User metrics validation - Reject weight less than or equal to zero
    Test steps: Send metrics payload with weight = 0
    Expected results: Validation fails
    """
    service = AuthService()
    mock_db = MagicMock()
    test_user_id = uuid.uuid4()

    # Payload with weight = 0
    invalid_metrics = {
        "age": 25,
        "weight": 0,
        "height": 180,
        "primary_goal": "lose_weight"
    }

    # Validation should fail either at the Pydantic schema level (ValidationError)
    # or inside the service (HTTPException)
    with pytest.raises((HTTPException, ValidationError)) as exc_info:
        data = UserMetricInput(**invalid_metrics)
        service.store_user_metrics(mock_db, test_user_id, data)
    
    # Note: Because the current codebase doesn't enforce weight > 0, 
    # this test will fail as "Failed: DID NOT RAISE" allowing you to file the bug ticket!

def test_tc_u05_reject_invalid_age():
    """
    TC-U05: User metrics validation - Reject age above allowed maximum
    Test steps: Send metrics payload with age = 151
    Expected results: Validation fails
    """
    service = AuthService()
    mock_db = MagicMock()
    test_user_id = uuid.uuid4()

    # Payload with age = 151 (above the logical maximum of 150)
    invalid_metrics = {
        "age": 151,
        "weight": 70.5,
        "height": 180,
        "primary_goal": "lose_weight"
    }

    # Validation should fail either at the Pydantic schema level (ValidationError)
    # or inside the service (HTTPException)
    with pytest.raises((HTTPException, ValidationError)) as exc_info:
        data = UserMetricInput(**invalid_metrics)
        service.store_user_metrics(mock_db, test_user_id, data)
    
    # Note: Because the current codebase doesn't enforce age <= 150, 
    # this test will also fail as "DID NOT RAISE" exposing another bug!
