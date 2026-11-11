from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field

Category = Literal["sales", "support", "complaint", "billing", "other"]


class RegisterRequest(BaseModel):
    business_name: str = Field(min_length=1, max_length=100)
    full_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class StaffCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    handles_category: Optional[Category] = None


class UserResponse(BaseModel):
    id: int
    business_id: int
    full_name: str
    email: EmailStr
    role: str
    handles_category: Optional[str] = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=30)


class CustomerResponse(BaseModel):
    id: int
    business_id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}