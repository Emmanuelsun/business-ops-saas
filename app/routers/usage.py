from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_owner
from app.models import Business, User

router = APIRouter(prefix="/usage", tags=["Usage"])

PLAN_LIMITS = {"free": 50, "pro": 500}


class UsageResponse(BaseModel):
    plan: str
    ai_calls_used: int
    ai_call_limit: int
    is_demo: bool


class PlanOption(BaseModel):
    name: str
    ai_call_limit: int


class PlanChange(BaseModel):
    plan: Literal["free", "pro"]


def usage_for(business: Business) -> UsageResponse:
    return UsageResponse(
        plan=business.plan,
        ai_calls_used=business.ai_calls_used,
        ai_call_limit=business.ai_call_limit,
        is_demo=business.is_demo,
    )


@router.get("", response_model=UsageResponse)
def get_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = db.get(Business, current_user.business_id)
    return usage_for(business)


@router.get("/plans", response_model=list[PlanOption])
def list_plans(current_user: User = Depends(get_current_user)):
    return [
        PlanOption(name=name, ai_call_limit=limit)
        for name, limit in PLAN_LIMITS.items()
    ]


@router.patch("/plan", response_model=UsageResponse)
def change_plan(
    data: PlanChange,
    owner: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    business = db.get(Business, owner.business_id)
    if business.is_demo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Plans cannot be changed in the demo.",
        )

    business.plan = data.plan
    business.ai_call_limit = PLAN_LIMITS[data.plan]
    db.commit()
    db.refresh(business)
    return usage_for(business)