from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: Optional[str] = "General"
    is_active: Optional[bool] = True
    google_auth_id: Optional[str] = None
    goal: Optional[str] = "maintain"

    
class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None