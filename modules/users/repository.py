import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from modules.users.models import HealthProfile, ProfileUser
from modules.users.schemas import UserMetricInput


class AuthRepository:
    """Handles all database operations for the users module."""

    # ──────────────────────────────────────────
    # Profile User
    # ──────────────────────────────────────────

    def get_email_by_username(self, db: Session, username: str) -> str | None:
        """
        Look up a user's email from profile.users by username.
        Returns the email string, or None if the username is not found.
        """
        profile = (
            db.query(ProfileUser)
            .filter(ProfileUser.username == username)
            .first()
        )
        return profile.email if profile else None

    def get_profile_by_username(self, db: Session, username: str):
        """Return the ProfileUser row for the given username, or None."""
        return (
            db.query(ProfileUser)
            .filter(ProfileUser.username == username)
            .first()
        )

    def create_profile_user(
        self,
        db: Session,
        user_id: uuid.UUID,
        full_name: str,
        username: str,
        email: str,
        role: str = "general",
    ) -> ProfileUser:
        """
        Upsert a row in profile.users after Supabase registration.
        The DB trigger may have already created the row with nulls —
        so we update it if it exists, insert if it doesn't.
        """
        profile = db.query(ProfileUser).filter(ProfileUser.id == user_id).first()

        if profile:
            # Row was created by the DB trigger — fill in the missing fields
            profile.full_name = full_name
            profile.username  = username
            profile.email     = email
            profile.role      = role
        else:
            # No trigger row — insert fresh
            profile = ProfileUser(
                id=user_id,
                full_name=full_name,
                username=username,
                email=email,
                role=role,
            )
            db.add(profile)

        db.commit()
        db.refresh(profile)
        return profile

    def get_all_users(self, db: Session):
        """Return all rows from profile.users (admin only)."""
        return (
            db.query(ProfileUser)
            .order_by(ProfileUser.created_at.desc())
            .all()
        )

    # ──────────────────────────────────────────
    # Health Profile
    # ──────────────────────────────────────────

    def get_health_profile_by_user_id(self, db: Session, user_id: uuid.UUID):
        """Return a user's health profile, or 404 if not found."""
        profile = (
            db.query(HealthProfile)
            .filter(HealthProfile.user_id == user_id)
            .first()
        )
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Health profile not found for this user.",
            )
        return profile

    def create_or_update_health_profile(
        self, db: Session, user_id: uuid.UUID, data: UserMetricInput
    ) -> HealthProfile:
        """Create or update the health profile for a user."""
        profile = (
            db.query(HealthProfile)
            .filter(HealthProfile.user_id == user_id)
            .first()
        )

        if profile:
            # ── Update existing record ──
            profile.age = data.age
            profile.weight = data.weight
            profile.height = data.height
            profile.gender = data.gender
            profile.primary_goal = data.primary_goal
            profile.fitness_level = data.fitness_level
            profile.activity_level = data.activity_level
            profile.daily_calorie_target = data.daily_calorie_target
            profile.injury_details = data.injury_details
            profile.recovery_stage = data.recovery_stage
            profile.medical_diet_notes = data.medical_diet_notes
        else:
            # ── Create new record ──
            profile = HealthProfile(
                user_id=user_id,
                age=data.age,
                weight=data.weight,
                height=data.height,
                gender=data.gender,
                primary_goal=data.primary_goal,
                fitness_level=data.fitness_level,
                activity_level=data.activity_level,
                daily_calorie_target=data.daily_calorie_target,
                injury_details=data.injury_details,
                recovery_stage=data.recovery_stage,
                medical_diet_notes=data.medical_diet_notes,
            )
            db.add(profile)

        db.commit()
        db.refresh(profile)
        return profile
