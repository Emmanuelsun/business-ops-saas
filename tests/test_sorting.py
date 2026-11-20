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


def test_assigning_clears_the_needs_sorting_flag(client, make_business):
    shop = make_business("Shop A", "owner@example.com")
    customer_id = create_customer(client, shop["headers"])
    use_up_ai_calls(shop["business_id"])

    created = client.post(
        "/enquiries",
        headers=shop["headers"],
        json={"customer_id": customer_id, "message": "Can I change my address?"},
    )
    assert created.status_code == 201, created.text
    enquiry = created.json()
    assert enquiry["needs_manual_sorting"] is True
    assert enquiry["status"] == "new"

    me = client.get("/auth/me", headers=shop["headers"]).json()
    response = client.patch(
        f"/enquiries/{enquiry['id']}/assign",
        headers=shop["headers"],
        json={"assigned_to": me["id"]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["needs_manual_sorting"] is False
    assert body["assigned_to"] == me["id"]
    assert body["status"] == "assigned"


def test_assigning_keeps_the_ai_category_and_priority(client, make_business):
    shop = make_business("Shop A", "owner@example.com")
    customer_id = create_customer(client, shop["headers"])

    created = client.post(
        "/enquiries",
        headers=shop["headers"],
        json={"customer_id": customer_id, "message": "I was charged twice."},
    )
    assert created.status_code == 201, created.text
    enquiry = created.json()
    assert enquiry["category"] == "billing"
    assert enquiry["needs_manual_sorting"] is False

    me = client.get("/auth/me", headers=shop["headers"]).json()
    response = client.patch(
        f"/enquiries/{enquiry['id']}/assign",
        headers=shop["headers"],
        json={"assigned_to": me["id"]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["category"] == "billing"
    assert body["priority"] == "high"
    assert body["needs_manual_sorting"] is False


# End of file.