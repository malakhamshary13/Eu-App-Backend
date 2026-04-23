
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import urllib.parse

from dotenv import load_dotenv
import os
from pydantic import BaseModel, ConfigDict

# Load environment variables from .env file
load_dotenv()

server = os.getenv("server", "")
database = os.getenv("database", "")
username = os.getenv("username", "")
password = os.getenv("password", "")

# URL encode the password in case it contains special characters
encoded_password = urllib.parse.quote_plus(password)

connection_string = (
    f"mssql+pyodbc://{username}:{encoded_password}@{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
)

engine = create_engine(connection_string)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class ORMBaseModel(BaseModel):
    """Base model with ORM mapping enabled for FastAPI/SQLAlchemy."""
    model_config = ConfigDict(from_attributes=True)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db  
    finally:
        db.close()