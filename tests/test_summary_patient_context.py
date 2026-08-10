"""Regression test: the /api/summary fallback path must use real patient
context and real RAG sources instead of hardcoded empty values.
"""
from fastapi.testclient import TestClient
from backend.api_app import app

client = TestClient(app)


def test_summary_includes_real_patient_context_and_sources():
    call_id = "summary-context-test"
    seed = client.post(
        "/api/assist",
        json={"transcript": "me duele mucho la herida", "call_id": call_id, "paciente_id": "P001"},
    )
    assert seed.status_code == 200
    seed_body = seed.json()
    assert seed_body["retrieval"], "expected assist to retrieve at least one RAG chunk"

    resp = client.post("/api/summary", json={"call_id": call_id, "paciente_id": "P001"})
    assert resp.status_code == 200
    body = resp.json()

    assert body["paciente_id"] == "P001"
    assert body["nombre"] != ""
    assert body["procedimiento"] != ""
    assert body["fuentes"], "expected summary to carry real RAG sources, not an empty list"
    assert all("id" in f for f in body["fuentes"])
