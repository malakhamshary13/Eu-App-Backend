import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from db.database import Base


class UserMealSchedule(Base):
    """Maps to tracker.user_meal_schedule."""
    __tablename__ = "user_meal_schedule"
    __table_args__ = {"schema": "tracker"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    meal_id = Column(UUID(as_uuid=True), ForeignKey("library.meals.id", ondelete="RESTRICT"), nullable=False)
    scheduled_date = Column(DateTime(timezone=True), nullable=False)
    meal_type = Column(String, nullable=False)
    is_eaten = Column(Boolean, nullable=False, default=False)
    eaten_date = Column(DateTime(timezone=True), nullable=True)

    meal = relationship("Meal", lazy="selectin")
