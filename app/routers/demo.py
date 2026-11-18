import os
import secrets
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Business,
    Customer,
    Enquiry,
    FollowUp,
    KnowledgeItem,
    Task,
    User,
)
from app.schemas import TokenResponse
from app.security import create_access_token, hash_password

router = APIRouter(prefix="/demo", tags=["Demo"])

CUSTOMERS = [
    ("Ngozi Adeyemi", "ngozi.adeyemi@example.com", "0803 555 0101"),
    ("Tunde Bakare", "tunde.bakare@example.com", "0805 555 0102"),
    ("Amara Okafor", "amara.okafor@example.com", "0807 555 0103"),
    ("Ibrahim Musa", "ibrahim.musa@example.com", "0809 555 0104"),
    ("Funke Balogun", "funke.balogun@example.com", "0802 555 0105"),
    ("Chinedu Eze", "chinedu.eze@example.com", "0806 555 0106"),
]

# (customer number, message, category, priority, status, assigned to,
#  needs manual sorting, days ago)
ENQUIRIES = [
    (0, "Hello, I would like to know the price of your large birthday cake.",
     "sales", "medium", "assigned", "sales", False, 1),
    (1, "I was charged twice for my last order. Please refund me immediately!",
     "billing", "high", "assigned", "owner", False, 4),
    (2, "How can I track my delivery? It has not arrived yet.",
     "support", "medium", "in_progress", "support", False, 3),
    (3, "Do you deliver to Ikeja on weekends?",
     None, None, "new", None, True, 0),
    (4, "The cake I received yesterday was damaged. I want to complain.",
     "complaint", "high", "assigned", "owner", False, 2),
    (5, "Do you have red velvet cupcakes in stock for Saturday?",
     "sales", "low", "resolved", "sales", False, 6),
    (0, "Can I change the delivery address on my order?",
     None, None, "new", None, True, 0),
    (2, "Do you offer gift wrapping for birthday orders?",
     "sales", "low", "assigned", "sales", False, 5),
]

NOTES = [
    (
        "Refund policy",
        "Customers can request a refund within 7 days of delivery if the "
        "item is unused. Refunds are paid back to the original payment "
        "method within 5 working days.",
    ),
    (
        "Opening hours",
        "We are open Monday to Saturday, 8am to 6pm. We are closed on "
        "Sundays and public holidays.",
    ),
    (
        "Delivery fees",
        "Delivery within Lagos costs 2,500 naira and takes 2 to 3 working "
        "days. Orders above 50,000 naira get free delivery.",
    ),
    (
        "Custom cake orders",
        "Custom cakes need at least 3 days notice. A 50 percent deposit is "
        "paid when the order is confirmed.",
    ),
]


def demo_enabled() -> bool:
    return os.getenv("DEMO_ENABLED", "false").lower() == "true"


def int_setting(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def cleanup_old_demos(db: Session) -> None:
    cutoff = func.now() - timedelta(hours=24)
    old_ids = [
        row[0]
        for row in db.query(Business.id)
        .filter(Business.is_demo.is_(True), Business.created_at < cutoff)
        .all()
    ]
    for business_id in old_ids:
        # Delete the rows that depend on others first.
        for model in (FollowUp, Task, Enquiry, Customer, KnowledgeItem, User):
            db.query(model).filter(model.business_id == business_id).delete()
        db.query(Business).filter(Business.id == business_id).delete()
    db.commit()


def seed_demo_business(db: Session, business: Business, tag: str) -> User:
    # Nobody logs in to these accounts with a password, so it is random.
    unusable_hash = hash_password(secrets.token_urlsafe(16))

    def make_user(name, email, role, category=None):
        user = User(
            business_id=business.id,
            full_name=name,
            email=email,
            password_hash=unusable_hash,
            role=role,
            handles_category=category,
        )
        db.add(user)
        db.flush()
        return user

    owner = make_user("Demo Owner", f"demo-{tag}@example.com", "owner")
    sales = make_user("Amaka Obi", f"demo-{tag}-amaka@example.com", "staff", "sales")
    support = make_user("Chidi Nwosu", f"demo-{tag}-chidi@example.com", "staff", "support")
    assignees = {"owner": owner.id, "sales": sales.id, "support": support.id, None: None}

    customers = []
    for name, email, phone in CUSTOMERS:
        customer = Customer(business_id=business.id, name=name, email=email, phone=phone)
        db.add(customer)
        customers.append(customer)
    db.flush()

    now = datetime.now()
    enquiries = []
    for number, message, category, priority, state, who, manual, days_ago in ENQUIRIES:
        when = now - timedelta(days=days_ago)
        enquiry = Enquiry(
            business_id=business.id,
            customer_id=customers[number].id,
            assigned_to=assignees[who],
            message=message,
            category=category,
            priority=priority,
            status=state,
            needs_manual_sorting=manual,
            created_at=when,
            updated_at=when,
        )
        db.add(enquiry)
        enquiries.append(enquiry)
    db.flush()

    follow_ups = [
        (
            1,
            "Hello Tunde, we are following up on your earlier message about "
            "the double charge. Is there anything else you need from us? "
            "Best regards, The team",
            "pending",
        ),
        (
            2,
            "Hello Amara, we are following up on your question about your "
            "delivery. Please let us know if you still need help. "
            "Best regards, The team",
            "pending",
        ),
        (
            7,
            "Hello Amara, we are following up on your gift wrapping "
            "question. Please let us know if there is anything else you "
            "would like to add. Best regards, The team",
            "done",
        ),
    ]
    for number, draft, state in follow_ups:
        db.add(
            FollowUp(
                business_id=business.id,
                enquiry_id=enquiries[number].id,
                draft_message=draft,
                status=state,
            )
        )

    db.add(
        Task(
            business_id=business.id,
            assigned_to=owner.id,
            enquiry_id=enquiries[4].id,
            customer_id=customers[4].id,
            title="Call Funke about the damaged cake",
            due_date=date.today() + timedelta(days=1),
            status="open",
        )
    )
    db.add(
        Task(
            business_id=business.id,
            assigned_to=sales.id,
            title="Check red velvet cupcake stock for Saturday",
            due_date=date.today() + timedelta(days=2),
            status="open",
        )
    )

    for title, content in NOTES:
        db.add(KnowledgeItem(business_id=business.id, title=title, content=content))

    return owner


@router.post(
    "/start",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_demo(db: Session = Depends(get_db)):
    if not demo_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The demo is not available.",
        )

    cleanup_old_demos(db)

    # Demos older than 24 hours are gone, so this counts the recent ones.
    daily_limit = int_setting("DEMO_DAILY_LIMIT", 30)
    running = db.query(Business).filter(Business.is_demo.is_(True)).count()
    if running >= daily_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The demo is very busy right now. Please try again later.",
        )

    business = Business(
        name="Sunrise Bakery (Demo)",
        plan="free",
        ai_calls_used=0,
        ai_call_limit=int_setting("DEMO_AI_CALLS", 10),
        is_demo=True,
    )
    db.add(business)
    db.flush()

    owner = seed_demo_business(db, business, secrets.token_hex(5))
    db.commit()
    return TokenResponse(access_token=create_access_token(owner.id))


# End of file.