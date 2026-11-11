from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Customer, Enquiry, Task, User
from app.schemas import TaskCreate, TaskResponse, TaskStatus

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def visible_tasks(db: Session, user: User):
    query = db.query(Task).filter(Task.business_id == user.business_id)
    if user.role != "owner":
        query = query.filter(Task.assigned_to == user.id)
    return query


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    title = data.title.strip()
    if not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title cannot be empty",
        )

    assignee_id = current_user.id
    if data.assigned_to is not None:
        assignee = (
            db.query(User)
            .filter(
                User.id == data.assigned_to,
                User.business_id == current_user.business_id,
            )
            .first()
        )
        if assignee is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        assignee_id = assignee.id

    if data.enquiry_id is not None:
        enquiry = (
            db.query(Enquiry)
            .filter(
                Enquiry.id == data.enquiry_id,
                Enquiry.business_id == current_user.business_id,
            )
            .first()
        )
        if enquiry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enquiry not found",
            )

    if data.customer_id is not None:
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

    task = Task(
        business_id=current_user.business_id,
        assigned_to=assignee_id,
        enquiry_id=data.enquiry_id,
        customer_id=data.customer_id,
        title=title,
        due_date=data.due_date,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    status_filter: Optional[TaskStatus] = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = visible_tasks(db, current_user)
    if status_filter:
        query = query.filter(Task.status == status_filter)
    return query.order_by(Task.id.desc()).all()


@router.patch("/{task_id}/complete", response_model=TaskResponse)
def complete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = visible_tasks(db, current_user).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    task.status = "done"
    db.commit()
    db.refresh(task)
    return task