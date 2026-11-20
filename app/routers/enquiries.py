import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.ai import AIError, classify_enquiry
from app.assignment import pick_assignee
from app.database import get_db
from app.dependencies import get_current_user, require_owner
from app.models import Customer, Enquiry, User
from app.schemas import (
    EnquiryAssign,
    EnquiryCreate,
    EnquiryResponse,
    EnquiryStatus,
    EnquiryStatusUpdate,
)
from app.usage import reserve_ai_call

logger = logging.getLogger("enquiries")

router = APIRouter(prefix="/enquiries", tags=["Enquiries"])


def visible_enquiries(db: Session, user: User):
    query = db.query(Enquiry).filter(Enquiry.business_id == user.business_id)
    if user.role != "owner":
        query = query.filter(Enquiry.assigned_to == user.id)
    return query


def find_enquiry(db: Session, user: User, enquiry_id: int) -> Enquiry:
    enquiry = (
        visible_enquiries(db, user).filter(Enquiry.id == enquiry_id).first()
    )
    if enquiry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enquiry not found",
        )
    return enquiry


@router.post(
    "",
    response_model=EnquiryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_enquiry(
    data: EnquiryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    message = data.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty",
        )

    customer = (
        db.query(Customer)
        .filter(
            Customer.id == data.customer_id,
            Customer.business_id == current_user.business_id,
        )
        .first()
    )
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    enquiry = Enquiry(
        business_id=current_user.business_id,
        customer_id=customer.id,
        message=message,
    )
    db.add(enquiry)
    db.commit()
    db.refresh(enquiry)

    if reserve_ai_call(db, current_user.business_id):
        try:
            result = classify_enquiry(message)
            enquiry.category = result["category"]
            enquiry.priority = result["priority"]

            assignee = pick_assignee(
                db, current_user.business_id, result["category"]
            )
            if assignee is not None:
                enquiry.assigned_to = assignee.id
                enquiry.status = "assigned"
        except AIError:
            enquiry.needs_manual_sorting = True
    else:
        logger.warning(
            "AI limit reached for business %s", current_user.business_id
        )
        enquiry.needs_manual_sorting = True

    db.commit()
    db.refresh(enquiry)
    return enquiry


@router.get("", response_model=list[EnquiryResponse])
def list_enquiries(
    status_filter: Optional[EnquiryStatus] = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = visible_enquiries(db, current_user)
    if status_filter:
        query = query.filter(Enquiry.status == status_filter)
    return query.order_by(Enquiry.id.desc()).all()


@router.get("/{enquiry_id}", response_model=EnquiryResponse)
def get_enquiry(
    enquiry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return find_enquiry(db, current_user, enquiry_id)


@router.patch("/{enquiry_id}/assign", response_model=EnquiryResponse)
def assign_enquiry(
    enquiry_id: int,
    data: EnquiryAssign,
    owner: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    enquiry = find_enquiry(db, owner, enquiry_id)

    assignee = (
        db.query(User)
        .filter(
            User.id == data.assigned_to,
            User.business_id == owner.business_id,
        )
        .first()
    )
    if assignee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    enquiry.assigned_to = assignee.id
    # A person has now handled this enquiry, so it no longer needs sorting.
    enquiry.needs_manual_sorting = False
    if enquiry.status == "new":
        enquiry.status = "assigned"

    db.commit()
    db.refresh(enquiry)
    return enquiry


@router.patch("/{enquiry_id}/status", response_model=EnquiryResponse)
def update_enquiry_status(
    enquiry_id: int,
    data: EnquiryStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enquiry = find_enquiry(db, current_user, enquiry_id)
    enquiry.status = data.status
    db.commit()
    db.refresh(enquiry)
    return enquiry


# End of file.