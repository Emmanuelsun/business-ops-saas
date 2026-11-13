from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_owner
from app.models import KnowledgeItem, User
from app.schemas import KnowledgeCreate, KnowledgeResponse

router = APIRouter(prefix="/knowledge", tags=["Knowledge"])


@router.post(
    "",
    response_model=KnowledgeResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_knowledge(
    data: KnowledgeCreate,
    owner: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    title = data.title.strip()
    content = data.content.strip()
    if not title or not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title and content cannot be empty",
        )

    item = KnowledgeItem(
        business_id=owner.business_id,
        title=title,
        content=content,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[KnowledgeResponse])
def list_knowledge(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.business_id == current_user.business_id)
        .order_by(KnowledgeItem.id)
        .all()
    )


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge(
    item_id: int,
    owner: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    item = (
        db.query(KnowledgeItem)
        .filter(
            KnowledgeItem.id == item_id,
            KnowledgeItem.business_id == owner.business_id,
        )
        .first()
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge item not found",
        )

    db.delete(item)
    db.commit()
    return None