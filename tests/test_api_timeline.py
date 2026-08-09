from fastapi.testclient import TestClient
from backend.api_app import app

client = TestClient(app)


def test_timeline_returns_turns_after_assist_calls():
    call_id = "timeline-test-call"
    seed_resp = client.post("/api/assist", json={"transcript": "hola, me duele", "call_id": call_id})
    assert seed_resp.status_code == 200

    resp = client.get(f"/api/timeline/{call_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["call_id"] == call_id
    assert isinstance(body["turns"], list)
    assert len(body["turns"]) >= 1
    assert set(body["turns"][0].keys()) == {"transcript", "response", "decision"}


def test_timeline_404_for_unknown_call_id():
    resp = client.get("/api/timeline/does-not-exist-call-id")
    assert resp.status_code == 404
