def make_staff(client, owner, email="staff@example.com", password="Password123"):
    response = client.post(
        "/users",
        headers=owner["headers"],
        json={
            "full_name": "Staff Member",
            "email": email,
            "password": password,
        },
    )
    assert response.status_code == 201, response.text

    login = client.post(
        "/auth/login", data={"username": email, "password": password}
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_plans_are_listed(client, make_business):
    shop = make_business("Shop A", "owner@example.com")

    response = client.get("/usage/plans", headers=shop["headers"])
    assert response.status_code == 200
    plans = {p["name"]: p["ai_call_limit"] for p in response.json()}
    assert plans == {"free": 50, "pro": 500}


def test_owner_can_switch_plans(client, make_business):
    shop = make_business("Shop A", "owner@example.com")

    start = client.get("/usage", headers=shop["headers"]).json()
    assert start["plan"] == "free"
    assert start["ai_call_limit"] == 50

    response = client.patch(
        "/usage/plan", headers=shop["headers"], json={"plan": "pro"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["plan"] == "pro"
    assert body["ai_call_limit"] == 500
    assert body["ai_calls_used"] == start["ai_calls_used"]

    response = client.patch(
        "/usage/plan", headers=shop["headers"], json={"plan": "free"}
    )
    assert response.json()["ai_call_limit"] == 50


def test_staff_cannot_switch_plans(client, make_business):
    owner = make_business("Shop A", "owner@example.com")
    staff_headers = make_staff(client, owner)

    response = client.patch(
        "/usage/plan", headers=staff_headers, json={"plan": "pro"}
    )
    assert response.status_code == 403


def test_unknown_plan_is_refused(client, make_business):
    shop = make_business("Shop A", "owner@example.com")

    response = client.patch(
        "/usage/plan", headers=shop["headers"], json={"plan": "platinum"}
    )
    assert response.status_code == 422


def test_plan_change_only_affects_own_business(client, make_business):
    a = make_business("Shop A", "a@example.com")
    b = make_business("Shop B", "b@example.com")

    client.patch("/usage/plan", headers=a["headers"], json={"plan": "pro"})

    b_usage = client.get("/usage", headers=b["headers"]).json()
    assert b_usage["plan"] == "free"
    assert b_usage["ai_call_limit"] == 50