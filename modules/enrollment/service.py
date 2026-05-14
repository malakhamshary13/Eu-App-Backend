import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from modules.enrollment.repository import EnrollmentRepository
from modules.enrollment.schemas import EnrollmentCreate, EnrollmentStatusUpdate

_repo = EnrollmentRepository()


class EnrollmentService:
    def create_enrollment(self, db: Session, user_id: uuid.UUID, data: EnrollmentCreate):
        return _repo.create_enrollment(db, user_id, data)

    def list_enrollments(self, db: Session, user_id: uuid.UUID, enroll_status: Optional[str] = None):
        return _repo.list_enrollments(db, user_id, enroll_status)

    def get_enrollment(self, db: Session, enrollment_id: uuid.UUID, user_id: uuid.UUID):
        return _repo.get_enrollment(db, enrollment_id, user_id)

    def get_active_workout_enrollment(self, db: Session, user_id: uuid.UUID):
        return _repo.get_active_workout_enrollment(db, user_id)

    def get_active_meal_enrollment(self, db: Session, user_id: uuid.UUID):
        return _repo.get_active_meal_enrollment(db, user_id)

    def update_status(self, db: Session, enrollment_id: uuid.UUID, user_id: uuid.UUID, data: EnrollmentStatusUpdate):
        return _repo.update_status(db, enrollment_id, user_id, data)

    def delete_enrollment(self, db: Session, enrollment_id: uuid.UUID, user_id: uuid.UUID):
        return _repo.delete_enrollment(db, enrollment_id, user_id)
