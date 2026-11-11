from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Customer, Enquiry, User
from app.schemas import EnquiryCreate, EnquiryResponse, EnquiryStatus

router = APIRouter(prefix="/enquiries", tags=["Enquiries"])


def visible_enquiries(db: Session, user: User):
    query = db.query(Enquiry).filter(Enquiry.business_id == user.business_id)
    if user.role != "owner":
        query = query.filter(Enquiry.assigned_to == user.id)
    return query


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
    enquiry = (
        visible_enquiries(db, current_user)
        .filter(Enquiry.id == enquiry_id)
        .first()
    )
    if enquiry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enquiry not found",
        )
    return enquiry