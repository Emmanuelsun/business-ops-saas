import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai import NOT_FOUND_TEXT, AIError, answer_question
from app.database import get_db
from app.dependencies import get_current_user, require_owner
from app.models import KnowledgeItem, User
from app.schemas import (
    AskRequest,
    AskResponse,
    KnowledgeCreate,
    KnowledgeResponse,
    SourceNote,
)
from app.usage import reserve_ai_call

logger = logging.getLogger("knowledge")

MAX_NOTES_CHARS = 12000

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


@router.post("/ask", response_model=AskResponse)
def ask_question(
    data: AskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    question = data.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty",
        )

    items = (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.business_id == current_user.business_id)
        .order_by(KnowledgeItem.id)
        .all()
    )

    notes = []
    total_size = 0
    for item in items:
        size = len(item.title) + len(item.content)
        if total_size + size > MAX_NOTES_CHARS:
            break
        notes.append(
            {"id": item.id, "title": item.title, "content": item.content}
        )
        total_size += size

    if not notes:
        return AskResponse(found=False, answer=NOT_FOUND_TEXT, sources=[])

    if not reserve_ai_call(db, current_user.business_id):
        logger.warning(
            "AI limit reached for business %s", current_user.business_id
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI usage limit reached for your plan",
        )

    try:
        result = answer_question(question, notes)
    except AIError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI service is unavailable. Please try again later.",
        )

    titles = {note["id"]: note["title"] for note in notes}
    sources = [
        SourceNote(id=source_id, title=titles[source_id])
        for source_id in result["source_ids"]
    ]
    return AskResponse(
        found=result["found"],
        answer=result["answer"],
        sources=sources,
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