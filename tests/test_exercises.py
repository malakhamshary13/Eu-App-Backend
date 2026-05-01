import pytest
import sys
import os
import uuid
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.exercises.service import ExerciseService
from modules.exercises.schemas import ExerciseCreate, ExerciseUpdate, PaginatedExercises, ExerciseResponse

@pytest.fixture
def service():
    return ExerciseService()

@pytest.fixture
def mock_db():
    return MagicMock()

@patch("modules.exercises.service._repo")
def test_tc_e01_list_exercises_pagination(mock_repo, service, mock_db):
    """
    TC-E01: List Exercises Pagination
    Test steps: Call list_exercises with specific page and page_size values
    Expected results: The repository is called with the exact pagination parameters and returns a paginated schema
    """
    # Setup mock return value
    mock_paginated_response = PaginatedExercises(
        items=[], total=0, page=2, page_size=10, pages=0
    )
    mock_repo.get_exercises.return_value = mock_paginated_response

    # Execute
    result = service.list_exercises(
        mock_db,
        page=2,
        page_size=10,
        exercise_type=None,
        muscle_group=None,
        equipment_category=None,
        search=None,
        use_profile=False,
        user_id=None
    )

    # Verify repo was called with correct pagination
    mock_repo.get_exercises.assert_called_once_with(
        mock_db,
        page=2,
        page_size=10,
        exercise_type=None,
        muscle_group=None,
        equipment_category=None,
        search=None,
        user_id=None
    )
    assert result.page == 2
    assert result.page_size == 10


@patch("modules.exercises.service._repo")
def test_tc_e02_list_exercises_with_profile(mock_repo, service, mock_db):
    """
    TC-E02: List Exercises with Profile Goal Filter
    Test steps: Call list_exercises with use_profile=True and use_profile=False
    Expected results: user_id is passed to the repo when True, and None is passed when False
    """
    test_user_id = uuid.uuid4()
    
    # Test with use_profile = True
    service.list_exercises(
        mock_db, page=1, page_size=20, exercise_type=None, muscle_group=None, 
        equipment_category=None, search=None, use_profile=True, user_id=test_user_id
    )
    # Assert user_id was passed
    mock_repo.get_exercises.assert_called_with(
        mock_db, page=1, page_size=20, exercise_type=None, muscle_group=None, 
        equipment_category=None, search=None, user_id=test_user_id
    )

    # Test with use_profile = False
    service.list_exercises(
        mock_db, page=1, page_size=20, exercise_type=None, muscle_group=None, 
        equipment_category=None, search=None, use_profile=False, user_id=test_user_id
    )
    # Assert user_id was NOT passed (should be None)
    mock_repo.get_exercises.assert_called_with(
        mock_db, page=1, page_size=20, exercise_type=None, muscle_group=None, 
        equipment_category=None, search=None, user_id=None
    )


@patch("modules.exercises.service._repo")
def test_tc_e03_get_exercise(mock_repo, service, mock_db):
    """
    TC-E03: Get Exercise by ID
    Test steps: Call get_exercise with a valid UUID
    Expected results: The repository is called and returns the exercise response
    """
    exercise_id = uuid.uuid4()
    mock_response = ExerciseResponse(id=exercise_id, title="Push Up")
    mock_repo.get_by_id.return_value = mock_response

    result = service.get_exercise(mock_db, exercise_id)

    mock_repo.get_by_id.assert_called_once_with(mock_db, exercise_id)
    assert result.title == "Push Up"


@patch("modules.exercises.service._repo")
def test_tc_e04_create_exercise(mock_repo, service, mock_db):
    """
    TC-E04: Create Exercise
    Test steps: Pass valid ExerciseCreate payload to create_exercise
    Expected results: The repository handles creation and returns an ExerciseResponse
    """
    create_payload = ExerciseCreate(title="Bench Press", muscle_group="chest")
    mock_response = ExerciseResponse(id=uuid.uuid4(), title="Bench Press", muscle_group="chest")
    mock_repo.create_exercise.return_value = mock_response

    result = service.create_exercise(mock_db, create_payload)

    mock_repo.create_exercise.assert_called_once_with(mock_db, create_payload)
    assert result.title == "Bench Press"


@patch("modules.exercises.service._repo")
def test_tc_e05_update_exercise(mock_repo, service, mock_db):
    """
    TC-E05: Update Exercise
    Test steps: Pass an ExerciseUpdate payload and UUID to update_exercise
    Expected results: The repository processes the update
    """
    exercise_id = uuid.uuid4()
    update_payload = ExerciseUpdate(title="Incline Bench Press")
    mock_response = ExerciseResponse(id=exercise_id, title="Incline Bench Press")
    mock_repo.update_exercise.return_value = mock_response

    result = service.update_exercise(mock_db, exercise_id, update_payload)

    mock_repo.update_exercise.assert_called_once_with(mock_db, exercise_id, update_payload)
    assert result.title == "Incline Bench Press"


@patch("modules.exercises.service._repo")
def test_tc_e06_delete_exercise(mock_repo, service, mock_db):
    """
    TC-E06: Delete Exercise
    Test steps: Pass an exercise UUID to delete_exercise
    Expected results: The repository processes the soft-delete and returns a success dictionary
    """
    exercise_id = uuid.uuid4()
    mock_repo.delete_exercise.return_value = {"success": True}

    result = service.delete_exercise(mock_db, exercise_id)

    mock_repo.delete_exercise.assert_called_once_with(mock_db, exercise_id)
    assert result["success"] is True
