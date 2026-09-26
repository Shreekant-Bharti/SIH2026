"""
Unit and integration tests for the /health and /model/info endpoints.
"""
from pathlib import Path
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure repo root and backend dir are in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent
for p in (str(REPO_ROOT), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.main import app
import backend.main as main_module
from backend.services.model_service import ModelService


@pytest.fixture
def client():
    """Provides a TestClient instance with initialized services."""
    return TestClient(app)


def test_root(client):
    """
    Test: GET / returns 200 with API status and docs link.
    """
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "/docs" in data["documentation"]


def test_health_ok(client):
    """
    Test 1: GET /health returns HTTP 200, status='ok', and model_loaded=True.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True
    assert data["model"] == "Ridge_Residual"
    assert data["model_version"] == "Ridge_Residual_v1"


def test_health_when_model_missing(client, monkeypatch):
    """
    Test: GET /health returns status='error' and model_loaded=False if model artifact is unavailable.
    """
    # Create an uninitialized/failed ModelService
    unloaded_ms = ModelService(model_path=Path("non_existent_model_path.joblib"))
    monkeypatch.setattr(main_module, "model_service", unloaded_ms)

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert data["model_loaded"] is False
    assert data["model"] == "Ridge_Residual"
    assert data["model_version"] == "Ridge_Residual_v1"


def test_model_info(client):
    """
    Test 2: GET /model/info returns Ridge_Residual_v1 metadata with 15 features.
    """
    response = client.get("/model/info")
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "Ridge_Residual"
    assert data["version"] == "Ridge_Residual_v1"
    assert data["feature_count"] == 15
    assert data["prediction_type"] == "Residual downscaling"
    assert data["status"] == "loaded"
