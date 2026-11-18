from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models import Business, Enquiry


def start_demo(client):
    response = client.post("/demo/start")
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_demo_is_off_by_default(client):
    response = client.post("/demo/start")
    assert response.status_code == 403


def test_demo_start_gives_a_ready_made_sandbox(client, monkeypatch):
    monkeypatch.setenv("DEMO_ENABLED", "true")
    headers = start_demo(client)

    assert len(client.get("/enquiries", headers=headers).json()) == 8
    assert len(client.get("/customers", headers=headers).json()) == 6
    assert len(client.get("/knowledge", headers=headers).json()) == 4
    assert len(client.get("/users", headers=headers).json()) == 3

    pending = client.get(
        "/follow-ups", headers=headers, params={"status": "pending"}
    ).json()
    assert len(pending) == 2

    usage = client.get("/usage", headers=headers).json()
    assert usage["is_demo"] is True
    assert usage["ai_call_limit"] == 10
    assert usage["ai_calls_used"] == 0


def test_two_demos_are_separate(client, monkeypatch):
    monkeypatch.setenv("DEMO_ENABLED", "true")
    a = start_demo(client)
    b = start_demo(client)

    created = client.post("/customers", headers=a, json={"name": "New Person"})
    assert created.status_code == 201, created.text

    assert len(client.get("/customers", headers=a).json()) == 7
    assert len(client.get("/customers", headers=b).json()) == 6


def test_demo_owner_cannot_change_plan(client, monkeypatch):
    monkeypatch.setenv("DEMO_ENABLED", "true")
    headers = start_demo(client)

    response = client.patch("/usage/plan", headers=headers, json={"plan": "pro"})
    assert response.status_code == 403

    usage = client.get("/usage", headers=headers).json()
    assert usage["plan"] == "free"
    assert usage["ai_call_limit"] == 10


def test_demo_daily_limit(client, monkeypatch):
    monkeypatch.setenv("DEMO_ENABLED", "true")
    monkeypatch.setenv("DEMO_DAILY_LIMIT", "1")

    start_demo(client)
    response = client.post("/demo/start")
    assert response.status_code == 429


def test_old_demos_are_cleaned_up(client, monkeypatch):
    monkeypatch.setenv("DEMO_ENABLED", "true")
    start_demo(client)

    db = SessionLocal()
    try:
        business = db.query(Business).filter(Business.is_demo.is_(True)).one()
        old_id = business.id
        business.created_at = datetime.now() - timedelta(days=2)
        db.commit()
    finally:
        db.close()

    start_demo(client)

    db = SessionLocal()
    try:
        ids = [
            b.id for b in db.query(Business).filter(Business.is_demo.is_(True)).all()
        ]
        assert len(ids) == 1
        assert old_id not in ids
        assert db.query(Enquiry).filter(Enquiry.business_id == old_id).count() == 0
    finally:
        db.close()


def test_real_businesses_are_not_demos(client, make_business):
    shop = make_business("Real Shop", "owner@example.com")

    usage = client.get("/usage", headers=shop["headers"]).json()
    assert usage["is_demo"] is False