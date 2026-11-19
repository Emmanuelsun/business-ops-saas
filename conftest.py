import os

from dotenv import load_dotenv
from sqlalchemy.engine import make_url

# Point the whole app at the TEST database before the app is imported.
load_dotenv()
_real_url = make_url(os.environ["DATABASE_URL"])
_test_url = _real_url.set(database="business_ops_test")
os.environ["DATABASE_URL"] = _test_url.render_as_string(hide_password=False)

# Fixed settings for the tests, whatever the real .env says.
os.environ["ALLOW_REGISTRATION"] = "false"
os.environ["DEMO_ENABLED"] = "false"
os.environ["DEMO_DAILY_LIMIT"] = "30"
os.environ["DEMO_AI_CALLS"] = "10"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app
from app.routers import enquiries as enquiries_module

# Safety check: refuse to run if the app is not using the test database.
if not str(engine.url.database).endswith("_test"):
    pytest.exit("Tests must run on a database whose name ends in _test.")


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    # Rebuild the throwaway test database from scratch for every test run.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(autouse=True)
def clean_database():
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
    yield


@pytest.fixture(autouse=True)
def fake_ai(monkeypatch):
    def fake_classify(message):
        return {"category": "billing", "priority": "high"}

    monkeypatch.setattr(enquiries_module, "classify_enquiry", fake_classify)


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def make_business(client, monkeypatch):
    def _make(name, email, password="Password123"):
        monkeypatch.setenv("ALLOW_REGISTRATION", "true")
        response = client.post(
            "/auth/register",
            json={
                "business_name": name,
                "full_name": f"{name} Owner",
                "email": email,
                "password": password,
            },
        )
        monkeypatch.setenv("ALLOW_REGISTRATION", "false")
        assert response.status_code == 201, response.text

        login = client.post(
            "/auth/login", data={"username": email, "password": password}
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        return {
            "headers": {"Authorization": f"Bearer {token}"},
            "business_id": response.json()["business_id"],
        }

    return _make


# End of file.