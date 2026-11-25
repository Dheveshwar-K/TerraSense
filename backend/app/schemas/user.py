from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

ValidRole = Literal["operator", "quality_engineer", "supervisor", "quality_manager", "admin"]


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=100)
    role: ValidRole = "operator"
    is_active: bool = True

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned.replace("_", "").replace("-", "").replace(".", "").isalnum():
            raise ValueError("Username may only contain alphanumeric characters, '.', '-', or '_'")
        return cleaned


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    email: Optional[str] = Field(default=None, min_length=5, max_length=100)
    role: Optional[ValidRole] = None
    is_active: Optional[bool] = None
    must_change_password: Optional[bool] = None


class UserLogin(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class DemoSwitchRequest(BaseModel):
    role: ValidRole
    user_id: Optional[str] = Field(default=None, max_length=50)


class UserResponse(UserBase):
    id: int
    must_change_password: bool = False
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = 1800
    user: UserResponse
