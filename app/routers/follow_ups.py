import logging
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai import AIError, draft_follow_up
from app.database import get_db
from app.dependencies import get_current_user, require_owner
from app.models import Customer, Enquiry, FollowUp, User
from app.schemas import FollowUpResponse, FollowUpRunResponse, FollowUpStatus
from app.usage import reserve_ai_call

logger = logging.getLogger("follow_ups")

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


@router.post("/run", response_model=FollowUpRunResponse)
def run_follow_ups(
    days: int = Query(default=2, ge=0, le=365),
    limit: int = Query(default=10, ge=1, le=50),
    owner: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    has_pending_follow_up = (
        db.query(FollowUp.id)
        .filter(
            FollowUp.enquiry_id == Enquiry.id,
            FollowUp.status == "pending",
        )
        .exists()
    )

    stale_enquiries = (
        db.query(Enquiry)
        .filter(
            Enquiry.business_id == owner.business_id,
            Enquiry.status != "resolved",
            Enquiry.updated_at <= func.now() - timedelta(days=days),
            ~has_pending_follow_up,
        )
        .order_by(Enquiry.updated_at, Enquiry.id)
        .limit(limit)
        .all()
    )

    checked = len(stale_enquiries)
    created = 0
    drafted = 0

    for enquiry in stale_enquiries:
        enquiry_id = enquiry.id
        customer = db.get(Customer, enquiry.customer_id)
        draft = None

        if customer is not None:
            if reserve_ai_call(db, owner.business_id):
                try:
                    draft = draft_follow_up(customer.name, enquiry.message)
                    drafted += 1
                except AIError:
                    logger.warning(
                        "Draft failed for enquiry %s", enquiry_id
                    )
            else:
                logger.warning(
                    "AI limit reached for business %s", owner.business_id
                )

        db.add(
            FollowUp(
                business_id=owner.business_id,
                enquiry_id=enquiry_id,
                draft_message=draft,
            )
        )
        db.commit()
        created += 1

    return FollowUpRunResponse(
        checked=checked, created=created, drafted=drafted
    )


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