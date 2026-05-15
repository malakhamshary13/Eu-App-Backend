from sqlalchemy import Column, String, Boolean, DateTime, Numeric, SmallInteger, Integer
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from db.database import Base


class ProfileUser(Base):
    """
    Extension table for Supabase auth.users.
    Stores app-specific user data such as username, role, etc.
    The 'id' column is a FK to auth.users(id) — enforced at the app level.
    """
    __tablename__ = "users"
    __table_args__ = {'schema': 'profile'}

    id = Column(UUID(as_uuid=True), primary_key=True)  # mirrors auth.users.id
    full_name = Column(String, nullable=True)
    username = Column(String, nullable=True, unique=True, index=True)
    email = Column(String, nullable=True, unique=True, index=True)  # cached for username login
    role = Column(String, nullable=False, default='general')
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# Note: User authentication is fully managed by Supabase Auth (auth.users).
# We do NOT define a SQLAlchemy User model — Supabase owns that schema and
# we must not try to create/alter tables there.


class HealthProfile(Base):
    """
    Stores fitness & health metrics for a user.
    user_id is BOTH the primary key and the FK to auth.users.id
    (one health profile per user, enforced at the DB level).
    """
    __tablename__ = "health_profiles"
    __table_args__ = {'schema': 'profile'}  # profile.health_profiles

    user_id            = Column(UUID(as_uuid=True), primary_key=True)  # PK == FK to auth.users
    age                = Column(SmallInteger, nullable=False)
    weight             = Column(Numeric(5, 2, asdecimal=True), nullable=False)   # kg
    height             = Column(Numeric(5, 2, asdecimal=True), nullable=False)   # cm
    # bmi is computed in the DB via trigger — do not insert
    gender             = Column(String(20), nullable=True)
    primary_goal       = Column(String(100), nullable=False)
    fitness_level      = Column(String(20), nullable=False, default='Beginner')
    activity_level     = Column(String(30), nullable=False, default='Sedentary')
    daily_calorie_target = Column(Integer, nullable=True)
    current_streak     = Column(Integer, nullable=False, default=0)
    longest_streak     = Column(Integer, nullable=False, default=0)
    injury_details     = Column(String(500), nullable=True)
    recovery_stage     = Column(String(100), nullable=True)
    medical_diet_notes = Column(String(1000), nullable=True)
    created_at         = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at         = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)