import uuid
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, condecimal, model_validator
from typing import Optional, Literal


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=72)
    role: Literal["Admin", "General", "Fitness", "Rehab", "Chronic"] = "General"
    is_active: bool = True
    google_auth_id: Optional[str] = None


class UserMetricInput(BaseModel):
    weight: condecimal(gt=0, le=Decimal("500.00"), max_digits=5, decimal_places=2) = Field(..., description="Weight in kg")
    height: condecimal(gt=0, le=Decimal("300.00"), max_digits=5, decimal_places=2) = Field(..., description="Height in cm")
    age: int = Field(..., gt=0, le=150, description="Age in years")
    gender: Optional[Literal["Male", "Female", "Other", "PreferNotToSay"]] = None
    primary_goal: Literal["LoseWeight", "GainMuscle", "Maintain", "Rehab", "General"] = "General"
    fitness_level: Optional[Literal["Beginner", "Intermediate", "Advanced"]] = "Beginner"
    activity_level: Optional[Literal["Sedentary", "LightlyActive", "ModeratelyActive", "VeryActive", "ExtraActive"]] = "Sedentary"
    daily_calorie_target: Optional[int] = None
    injury_details: Optional[str] = None
    recovery_stage: Optional[str] = None
    medical_diet_notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_bmi_within_db_limits(self):
        if self.weight is not None and self.height is not None:
            height_m = self.height / Decimal("100")
            bmi = self.weight / (height_m ** 2)
            if bmi > Decimal("999.99"):
                raise ValueError(
                    f"The weight/height combination produces a BMI of {bmi:.2f}, "
                    f"which exceeds database limits. Use realistic values "
                    f"(for example, weight=70 kg and height=175 cm)."
                )
        return self


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: uuid.UUID


class TokenData(BaseModel):
    username: str