from sqlalchemy import Column, Integer, String, Text
from db.database import Base


class Workout(Base):
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    goal = Column(String, nullable=False)
    duration_minutes = Column(Integer, nullable=True)
    difficulty = Column(String, nullable=True)