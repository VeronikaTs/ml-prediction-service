import os
import sys

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
os.environ["MODEL_PATH"] = os.path.join(
    PROJECT_ROOT, "model", "model.pkl"
)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "app"))

from app import app  # noqa: E402


def test_health():
    client = app.test_client()
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_predict_no_features():
    client = app.test_client()
    response = client.post("/predict", json={})

    assert response.status_code == 400
