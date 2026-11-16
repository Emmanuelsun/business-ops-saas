import httpx

BASE_URL = "http://127.0.0.1:8000"


class SessionExpired(Exception):
    pass


def login(email, password):
    try:
        response = httpx.post(
            f"{BASE_URL}/auth/login",
            data={"username": email, "password": password},
            timeout=10,
        )
    except httpx.RequestError:
        raise RuntimeError("Cannot reach the app. Is FastAPI running?")

    if response.status_code == 200:
        return response.json()["access_token"]
    return None


def get(path, token, params=None):
    try:
        response = httpx.get(
            f"{BASE_URL}{path}",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=10,
        )
    except httpx.RequestError:
        raise RuntimeError("Cannot reach the app. Is FastAPI running?")

    if response.status_code == 401:
        raise SessionExpired()

    response.raise_for_status()
    return response.json()


def patch(path, token):
    try:
        response = httpx.patch(
            f"{BASE_URL}{path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except httpx.RequestError:
        raise RuntimeError("Cannot reach the app. Is FastAPI running?")

    if response.status_code == 401:
        raise SessionExpired()

    response.raise_for_status()
    return response.json()


def post(path, token, body):
    try:
        response = httpx.post(
            f"{BASE_URL}{path}",
            headers={"Authorization": f"Bearer {token}"},
            json=body,
            timeout=30,
        )
    except httpx.RequestError:
        raise RuntimeError("Cannot reach the app. Is FastAPI running?")

    if response.status_code == 401:
        raise SessionExpired()

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = None
        raise RuntimeError(detail or f"The app returned error {response.status_code}.")

    return response.json()