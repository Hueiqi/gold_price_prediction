"""Basic API contract tests. These mock the DB/model layer so they can run
without a live Postgres instance or a trained model artifact.
"""
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_root_ok():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "AURIC" in resp.text
    assert client.get("/api/health").json()["status"] == "ok"


def test_predict_returns_503_when_no_model():
    with patch("src.api.main.predict_next_price", side_effect=FileNotFoundError("no model")):
        resp = client.get("/api/predict")
        assert resp.status_code == 503


def test_predict_rejects_invalid_horizon():
    resp = client.get("/api/predict", params={"days_ahead": 0})
    assert resp.status_code == 422  # FastAPI validation error, ge=1

    resp = client.get("/api/predict", params={"days_ahead": 999})
    assert resp.status_code == 422  # le=30
