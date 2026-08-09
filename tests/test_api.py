"""Tests for FastAPI endpoints."""
import pytest
from fastapi.testclient import TestClient
from backend.api_app import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_assist_endpoint_requires_transcript():
    response = client.post("/api/assist", json={})
    assert response.status_code == 422


def test_assist_endpoint_empty_transcript():
    response = client.post("/api/assist", json={"transcript": ""})
    assert response.status_code in (400, 503)


def test_admin_list_documents():
    response = client.get("/admin/documents")
    assert response.status_code == 200
    assert "documents" in response.json()


def test_admin_delete_nonexistent():
    response = client.post("/admin/delete", json={"doc_id": "nonexistent_id"})
    assert response.status_code in (200, 404)


def test_metrics_endpoint():
    response = client.get("/api/metrics")
    assert response.status_code == 200
