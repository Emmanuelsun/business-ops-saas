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


def test_staff_cannot_do_owner_only_actions(client, make_business):
    owner = make_business("Shop A", "owner@example.com")
    staff_headers = make_staff(client, owner)

    owner_only_actions = [
        ("GET", "/users", None),
        (
            "POST",
            "/users",
            {
                "full_name": "Another Staff",
                "email": "another@example.com",
                "password": "Password123",
            },
        ),
        ("POST", "/knowledge", {"title": "Note", "content": "Some content"}),
        ("POST", "/follow-ups/run", None),
        ("DELETE", "/customers/1", None),
        ("PATCH", "/enquiries/1/assign", {"assigned_to": 1}),
    ]

    for method, path, body in owner_only_actions:
        response = client.request(method, path, headers=staff_headers, json=body)
        assert response.status_code == 403, (
            f"{method} {path} gave {response.status_code}, expected 403"
        )


def test_staff_can_still_use_everyday_features(client, make_business):
    owner = make_business("Shop A", "owner@example.com")
    staff_headers = make_staff(client, owner)

    response = client.post(
        "/customers", headers=staff_headers, json={"name": "Walk-in Customer"}
    )
    assert response.status_code == 201, response.text

    assert client.get("/knowledge", headers=staff_headers).status_code == 200
    assert client.get("/usage", headers=staff_headers).status_code == 200