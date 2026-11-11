from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_owner
from app.models import User
from app.schemas import StaffCreate, UserResponse
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_staff(
    data: StaffCreate,
    owner: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    email = data.email.lower()

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        business_id=owner.business_id,
        full_name=data.full_name,
        email=email,
        password_hash=hash_password(data.password),
        role="staff",
        handles_category=data.handles_category,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=list[UserResponse])
def list_users(
    owner: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    return (
        db.query(User)
        .filter(User.business_id == owner.business_id)
        .order_by(User.id)
        .all()
    )