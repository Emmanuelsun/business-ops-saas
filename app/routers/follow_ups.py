from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Enquiry, FollowUp, User
from app.schemas import FollowUpResponse, FollowUpStatus

router = APIRouter(prefix="/follow-ups", tags=["Follow-ups"])


def visible_follow_ups(db: Session, user: User):
    query = db.query(FollowUp).filter(FollowUp.business_id == user.business_id)
    if user.role != "owner":
        query = query.join(Enquiry, FollowUp.enquiry_id == Enquiry.id).filter(
            Enquiry.assigned_to == user.id
        )
    return query


@router.get("", response_model=list[FollowUpResponse])
def list_follow_ups(
    status_filter: Optional[FollowUpStatus] = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = visible_follow_ups(db, current_user)
    if status_filter:
        query = query.filter(FollowUp.status == status_filter)
    return query.order_by(FollowUp.id.desc()).all()


@router.patch("/{follow_up_id}/done", response_model=FollowUpResponse)
def mark_follow_up_done(
    follow_up_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    follow_up = (
        visible_follow_ups(db, current_user)
        .filter(FollowUp.id == follow_up_id)
        .first()
    )
    if follow_up is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow-up not found",
        )

    follow_up.status = "done"
    db.commit()
    db.refresh(follow_up)
    return follow_up