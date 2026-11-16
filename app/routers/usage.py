from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Business, User

router = APIRouter(prefix="/usage", tags=["Usage"])


class UsageResponse(BaseModel):
    plan: str
    ai_calls_used: int
    ai_call_limit: int


@router.get("", response_model=UsageResponse)
def get_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = db.get(Business, current_user.business_id)
    return UsageResponse(
        plan=business.plan,
        ai_calls_used=business.ai_calls_used,
        ai_call_limit=business.ai_call_limit,
    )