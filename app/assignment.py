from typing import Optional

from sqlalchemy.orm import Session

from app.models import User


def pick_assignee(
    db: Session, business_id: int, category: str
) -> Optional[User]:
    staff_member = (
        db.query(User)
        .filter(
            User.business_id == business_id,
            User.role == "staff",
            User.handles_category == category,
        )
        .order_by(User.id)
        .first()
    )
    if staff_member is not None:
        return staff_member

    return (
        db.query(User)
        .filter(User.business_id == business_id, User.role == "owner")
        .order_by(User.id)
        .first()
    )