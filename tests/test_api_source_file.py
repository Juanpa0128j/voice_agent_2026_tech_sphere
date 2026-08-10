"""GET /api/source/{doc_id} serves the raw source document so the frontend
can link 'Fuentes utilizadas' chips to the actual file, with a
path-traversal guard since doc_id is attacker-controlled input.
"""
from fastapi.testclient import TestClient
from backend.api_app import app

client = TestClient(app)


def test_source_file_serves_known_document():
    docs = client.get("/admin/documents").json()["documents"]
    assert docs, "expected at least one indexed document to test against"
    doc_id = docs[0]["doc_id"]

    resp = client.get(f"/api/source/{doc_id}")
    assert resp.status_code == 200
    assert len(resp.content) > 0


def test_source_file_rejects_path_traversal():
    resp = client.get("/api/source/..%2F..%2F..%2Fetc%2Fpasswd")
    assert resp.status_code in (400, 404)


def test_source_file_404_for_unknown_doc():
    resp = client.get("/api/source/does-not-exist.pdf")
    assert resp.status_code == 404
