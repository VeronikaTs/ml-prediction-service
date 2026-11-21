import os
import sys


sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    ),
)

from app import app  # noqa: E402


def test_health():
    client = app.test_client()
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "service": "logger",
    }


def test_log_missing_fields():
    client = app.test_client()
    response = client.post("/log", json={})

    assert response.status_code == 400
    assert "error" in response.get_json()
