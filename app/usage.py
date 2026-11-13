from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import Business


def reserve_ai_call(db: Session, business_id: int) -> bool:
    result = db.execute(
        update(Business)
        .where(
            Business.id == business_id,
            Business.ai_calls_used < Business.ai_call_limit,
        )
        .values(ai_calls_used=Business.ai_calls_used + 1)
    )
    db.commit()
    return result.rowcount == 1