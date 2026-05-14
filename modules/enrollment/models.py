import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.database import Base


class UserPlanEnrollment(Base):
    """
    Maps to plans.user_plan_enrollments.

    A user may be enrolled in at most one workout plan and one meal plan
    at a time in 'active' status (enforced at the application layer).

    Status lifecycle:
      active → paused → active   (resumable)
      active → completed          (terminal — plan finished)
      active → dropped            (terminal — user quit)
    """
    __tablename__ = "user_plan_enrollments"
    __table_args__ = {"schema": "plans"}

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True), nullable=False)
    workout_plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("plans.workout_plans.id", ondelete="SET NULL"),
        nullable=True,
    )
    meal_plan_id    = Column(
        UUID(as_uuid=True),
        ForeignKey("plans.meal_plans.id", ondelete="SET NULL"),
        nullable=True,
    )
    status          = Column(String, nullable=False, default="active")
    # 'active' | 'paused' | 'completed' | 'dropped'
    enrolled_at     = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    workout_plan = relationship("WorkoutPlan", lazy="selectin", foreign_keys=[workout_plan_id])
