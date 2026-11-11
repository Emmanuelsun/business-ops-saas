from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_owner
from app.models import Customer, Enquiry, Task, User
from app.schemas import CustomerCreate, CustomerResponse, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["Customers"])


def find_customer(db: Session, customer_id: int, business_id: int) -> Customer:
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.business_id == business_id,
        )
        .first()
    )
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )
    return customer


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer(
    data: CustomerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    customer = Customer(
        business_id=current_user.business_id,
        name=data.name,
        email=data.email.lower() if data.email else None,
        phone=data.phone,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("", response_model=list[CustomerResponse])
def list_customers(
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Customer).filter(
        Customer.business_id == current_user.business_id
    )
    if search:
        query = query.filter(Customer.name.ilike(f"%{search}%"))
    return query.order_by(Customer.id).all()


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return find_customer(db, customer_id, current_user.business_id)


@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int,
    data: CustomerUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    customer = find_customer(db, customer_id, current_user.business_id)

    updates = data.model_dump(exclude_unset=True)

    if "name" in updates and updates["name"] is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name cannot be empty",
        )

    if updates.get("email"):
        updates["email"] = updates["email"].lower()

    for field, value in updates.items():
        setattr(customer, field, value)

    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: int,
    owner: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    customer = find_customer(db, customer_id, owner.business_id)

    has_enquiries = (
        db.query(Enquiry).filter(Enquiry.customer_id == customer.id).first()
    )
    has_tasks = db.query(Task).filter(Task.customer_id == customer.id).first()

    if has_enquiries or has_tasks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer has enquiries or tasks and cannot be deleted",
        )

    db.delete(customer)
    db.commit()
    return None