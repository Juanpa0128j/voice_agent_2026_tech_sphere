"""Regression test: greeting turns must never run clinical decision logic.

decision.decide() sends the transcript to an LLM for structured symptom
extraction. On an empty greeting transcript, that call has been observed
to hallucinate plausible-looking symptoms (e.g. dolor_eva, movilidad
limitada) from nothing — a genuine clinical hallucination the rubric
explicitly penalizes. The fix: greeting turns get a fixed safe decision
(verde, no alert, no rationale) without ever calling the decision engine.
"""
from fastapi.testclient import TestClient
from backend.api_app import app

client = TestClient(app)


def test_greeting_never_produces_a_risk_finding():
    resp = client.post(
        "/api/assist",
        json={"transcript": "", "greeting": True, "call_id": "greeting-no-decision-test"},
    )
    assert resp.status_code == 200
    body = resp.json()
    decision = body["decision"]

    assert decision["label"] == "verde"
    assert decision["alert"] is False
    assert decision["score"] == 0
