def test_registration_is_closed_by_default(client):
    response = client.post(
        "/auth/register",
        json={
            "business_name": "Closed Shop",
            "full_name": "Closed Owner",
            "email": "owner@example.com",
            "password": "Password123",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Registration is closed."


def test_login_with_correct_password(client, make_business):
    make_business("Login Shop", "owner@example.com", "Password123")

    response = client.post(
        "/auth/login",
        data={"username": "owner@example.com", "password": "Password123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_with_wrong_password_is_refused(client, make_business):
    make_business("Login Shop", "owner@example.com", "Password123")

    response = client.post(
        "/auth/login",
        data={"username": "owner@example.com", "password": "WrongPassword1"},
    )
    assert response.status_code == 401