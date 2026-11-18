def create_customer(client, headers, name="Ngozi"):
    response = client.post("/customers", headers=headers, json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_business_b_cannot_see_business_a_customers(client, make_business):
    a = make_business("Shop A", "a@example.com")
    b = make_business("Shop B", "b@example.com")
    customer_id = create_customer(client, a["headers"])

    assert client.get("/customers", headers=b["headers"]).json() == []
    response = client.get(f"/customers/{customer_id}", headers=b["headers"])
    assert response.status_code == 404


def test_business_b_cannot_see_or_use_business_a_enquiries(client, make_business):
    a = make_business("Shop A", "a@example.com")
    b = make_business("Shop B", "b@example.com")
    customer_id = create_customer(client, a["headers"])

    created = client.post(
        "/enquiries",
        headers=a["headers"],
        json={"customer_id": customer_id, "message": "I was charged twice."},
    )
    assert created.status_code == 201, created.text
    enquiry_id = created.json()["id"]

    assert client.get("/enquiries", headers=b["headers"]).json() == []
    response = client.get(f"/enquiries/{enquiry_id}", headers=b["headers"])
    assert response.status_code == 404

    response = client.post(
        "/enquiries",
        headers=b["headers"],
        json={"customer_id": customer_id, "message": "Sneaky message"},
    )
    assert response.status_code == 404


def test_business_b_cannot_see_or_delete_business_a_notes(client, make_business):
    a = make_business("Shop A", "a@example.com")
    b = make_business("Shop B", "b@example.com")

    created = client.post(
        "/knowledge",
        headers=a["headers"],
        json={"title": "Refund policy", "content": "Refunds within 7 days."},
    )
    assert created.status_code == 201, created.text
    note_id = created.json()["id"]

    assert client.get("/knowledge", headers=b["headers"]).json() == []
    response = client.delete(f"/knowledge/{note_id}", headers=b["headers"])
    assert response.status_code == 404

    notes_for_a = client.get("/knowledge", headers=a["headers"]).json()
    assert len(notes_for_a) == 1