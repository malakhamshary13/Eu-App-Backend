import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic import BaseModel, ConfigDict
from supabase import create_client, Client

# --- 1. Configuration & Setup ---
load_dotenv()

DATABASE_URL = os.environ.get("DB_URL") or ""
SUPABASE_URL = os.environ.get("SUPABASE_URL") or ""
SUPABASE_KEY = os.environ.get("PUBLIC_ANON_KEY") or ""

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials in .env file.")

# SQLAlchemy Setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Supabase Client Setup (for Auth)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_db():
    db = SessionLocal()
    try:
        yield db  
    finally:
        db.close()

class ORMBaseModel(BaseModel):
    """Base model with ORM mapping enabled for FastAPI/SQLAlchemy."""
    model_config = ConfigDict(from_attributes=True)



# yield turns a normal function into a generator.
# In the context of database connections, it acts as an elegant setup-and-teardown mechanism without polluting your core business logic.
# The yield pattern completely replaces the need to write repetitive try...finally blocks inside every single API endpoint.
# When a function containing yield is executed by the framework, it pauses at the yield statement, hands control over to your API route, and resumes only after the API route finishes (or crashes).

# depends on the above get_db function to provide a database session to routes that need it, ensuring proper connection management.
# depends mean Before you run this API endpoint, go fetch the things it needs to do its job, and hand them to it and it stops at yield until you give it the thing it needs, then it continues running the code after yield and once it's done, it goes back to the code before yield and runs that to clean up.



# Use yield to guarantee that setup (connecting) and teardown (disconnecting) always happen in pairs, even during application errors.

# Use Depends to inject that connection directly into your functions, keeping your code decoupled and easy to test.