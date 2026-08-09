from fastapi.testclient import TestClient
from backend.api_app import app

client = TestClient(app)


def test_assist_includes_patient_context_when_paciente_id_known():
    resp = client.post(
        "/api/assist",
        json={"transcript": "me duele un poco", "paciente_id": "P001", "call_id": "test-call-1"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "patient" in body
    assert body["patient"] is not None
    assert set(body["patient"].keys()) == {
        "paciente_id", "nombre", "procedimiento",
        "dia_postoperatorio", "comorbilidades", "eps",
    }


def test_assist_patient_is_none_when_paciente_id_missing():
    resp = client.post(
        "/api/assist",
        json={"transcript": "hola", "call_id": "test-call-2"},
    )
    assert resp.status_code == 200
    assert resp.json()["patient"] is None
