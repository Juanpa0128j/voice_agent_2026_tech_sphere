"""Tests for the voice pipeline endpoints (/api/stt, /api/tts) and static routes."""
from fastapi.testclient import TestClient

from backend.api_app import app

client = TestClient(app)


def test_stt_missing_file():
    response = client.post("/api/stt")
    assert response.status_code == 422


def test_stt_bad_extension():
    response = client.post(
        "/api/stt",
        files={"file": ("malware.exe", b"MZ", "application/octet-stream")},
    )
    assert response.status_code == 400


def test_stt_valid_format_returns_200_or_503():
    # Without a GROQ_API_KEY in the test env the lazy client 503s;
    # with one (or mocked) it would 200. Either is acceptable here.
    response = client.post(
        "/api/stt",
        files={"file": ("turno.webm", b"fake-webm-bytes", "audio/webm")},
    )
    assert response.status_code in (200, 503)


def test_tts_empty_text():
    response = client.post("/api/tts", json={"text": ""})
    assert response.status_code == 422


def test_tts_too_long():
    response = client.post("/api/tts", json={"text": "x" * 5000})
    assert response.status_code == 422


def test_tts_happy_path_or_unavailable():
    # edge-tts is installed locally, so this should stream; on CI without
    # network to the edge service it may 503. Accept either, but never 500.
    response = client.post("/api/tts", json={"text": "Hola, ¿cómo te sientes hoy?"})
    assert response.status_code in (200, 503)
    if response.status_code == 200:
        assert response.headers["content-type"].startswith("audio/mpeg")


def test_index_html_route():
    response = client.get("/index.html")
    assert response.status_code == 200
    assert "MediCol" in response.text


def test_favicon_route():
    response = client.get("/favicon.ico")
    assert response.status_code == 204
