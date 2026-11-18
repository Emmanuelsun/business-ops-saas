from app.database import SessionLocal
from app.models import Business


def use_up_ai_calls(business_id):
    db = SessionLocal()
    try:
        business = db.query(Business).filter(Business.id == business_id).one()
        business.ai_calls_used = business.ai_call_limit
        db.commit()
    finally:
        db.close()


def create_customer(client, headers):
    response = client.post("/customers", headers=headers, json={"name": "Ngozi"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_each_enquiry_uses_exactly_one_ai_call(client, make_business):
    shop = make_business("Shop A", "owner@example.com")
    customer_id = create_customer(client, shop["headers"])

    response = client.post(
        "/enquiries",
        headers=shop["headers"],
        json={"customer_id": customer_id, "message": "Can I get a refund?"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["category"] == "billing"
    assert body["priority"] == "high"
    assert body["needs_manual_sorting"] is False

    usage = client.get("/usage", headers=shop["headers"]).json()
    assert usage["ai_calls_used"] == 1


def test_enquiry_is_still_saved_when_the_limit_is_reached(client, make_business):
    shop = make_business("Shop A", "owner@example.com")
    customer_id = create_customer(client, shop["headers"])
    use_up_ai_calls(shop["business_id"])

    response = client.post(
        "/enquiries",
        headers=shop["headers"],
        json={"customer_id": customer_id, "message": "Do you deliver on Sundays?"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["needs_manual_sorting"] is True
    assert body["category"] is None
    assert body["status"] == "new"

    usage = client.get("/usage", headers=shop["headers"]).json()
    assert usage["ai_calls_used"] == usage["ai_call_limit"]

    saved = client.get("/enquiries", headers=shop["headers"]).json()
    assert len(saved) == 1