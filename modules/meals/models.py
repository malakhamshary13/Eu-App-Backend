from sqlalchemy import Column, Integer, String, Text
from db.database import Base


class Meal(Base):
    __tablename__ = "meals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    goal = Column(String, nullable=False)
    calories = Column(Integer, nullable=True)
    protein = Column(Integer, nullable=True)