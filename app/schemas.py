from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field

Category = Literal["sales", "support", "complaint", "billing", "other"]
EnquiryStatus = Literal["new", "assigned", "in_progress", "resolved"]
TaskStatus = Literal["open", "done"]
FollowUpStatus = Literal["pending", "done"]


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


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
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


class EnquiryCreate(BaseModel):
    customer_id: int
    message: str = Field(min_length=1, max_length=5000)


class EnquiryAssign(BaseModel):
    assigned_to: int


class EnquiryStatusUpdate(BaseModel):
    status: EnquiryStatus


class EnquiryResponse(BaseModel):
    id: int
    business_id: int
    customer_id: int
    assigned_to: Optional[int] = None
    message: str
    category: Optional[str] = None
    priority: Optional[str] = None
    status: str
    needs_manual_sorting: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    due_date: Optional[date] = None
    assigned_to: Optional[int] = None
    enquiry_id: Optional[int] = None
    customer_id: Optional[int] = None


class TaskResponse(BaseModel):
    id: int
    business_id: int
    assigned_to: Optional[int] = None
    enquiry_id: Optional[int] = None
    customer_id: Optional[int] = None
    title: str
    due_date: Optional[date] = None
    status: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class KnowledgeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=5000)


class KnowledgeResponse(BaseModel):
    id: int
    business_id: int
    title: str
    content: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class SourceNote(BaseModel):
    id: int
    title: str


class AskResponse(BaseModel):
    found: bool
    answer: str
    sources: list[SourceNote]


class FollowUpResponse(BaseModel):
    id: int
    business_id: int
    enquiry_id: int
    draft_message: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}