"""Regression test: the greeting turn must be stored in conversation
history so the LLM has memory of it on the next turn.

Previously conversation.append() explicitly skipped greeting turns, so
turn 2's history was empty — the LLM had no idea it already introduced
itself, and re-introduced itself again ("Hola, soy MediCol...") on the
very next real turn, which reads as broken/repetitive in a real call.
"""
from fastapi.testclient import TestClient
from backend.api_app import app
from backend.api_app import get_conversation_store

client = TestClient(app)


def test_greeting_turn_is_stored_in_conversation_history():
    call_id = "greeting-history-test"
    greet = client.post(
        "/api/assist",
        json={"transcript": "", "greeting": True, "call_id": call_id},
    )
    assert greet.status_code == 200

    conversation = get_conversation_store()
    history = conversation.history(call_id)
    assert len(history) == 1, "greeting turn should be recorded in history"
    assert history[0]["response"] == greet.json()["response"]


def test_second_turn_history_includes_the_greeting_response():
    call_id = "greeting-history-test-2"
    client.post(
        "/api/assist",
        json={"transcript": "", "greeting": True, "call_id": call_id},
    )

    resp = client.get(f"/api/timeline/{call_id}")
    assert resp.status_code == 200
    turns = resp.json()["turns"]
    assert len(turns) == 1
    assert turns[0]["response"]
