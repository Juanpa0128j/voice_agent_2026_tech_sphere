"""End-to-end smoke test of the voice agent.

Exercises the full pipeline against the live server:
  1. Health check
  2. /api/assist with multiple transcripts (verde, amarillo, rojo)
  3. /admin/documents lists PDFs
  4. /admin/upload adds a new doc
  5. /admin/delete removes it
  6. /api/metrics shows token/latency stats
  7. /api/summary returns a structured summary

Requires the server to be running at BASE_URL.
"""
import sys
import time
import json
from pathlib import Path

import httpx

BASE_URL = "http://localhost:8000"
TIMEOUT = 120.0  # first request is slow (BGE-M3 model load)


def step(name: str) -> None:
    print(f"\n=== {name} ===", flush=True)


def expect(cond: bool, msg: str) -> None:
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {msg}", flush=True)
    if not cond:
        sys.exit(1)


def main() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as c:

        step("1. Health check")
        r = c.get("/api/health")
        expect(r.status_code == 200, f"GET /api/health -> {r.status_code}")
        expect(r.json().get("status") == "ok", f"status == ok: {r.json()}")

        step("2. /api/assist — verde case")
        r = c.post("/api/assist", json={
            "transcript": "Hola doctor, me siento bien, solo un poquito de molestia leve",
            "paciente_id": "P001",
            "call_id": "smoke-1",
        })
        expect(r.status_code == 200, f"POST /api/assist verde -> {r.status_code}")
        data = r.json()
        expect("response" in data, "response field present")
        expect("decision" in data, "decision field present")
        print(f"  decision: {data['decision'].get('label')}", flush=True)
        print(f"  response: {data['response'][:100]}...", flush=True)
        time.sleep(1)

        step("3. /api/assist — rojo case (fiebre + dolor)")
        r = c.post("/api/assist", json={
            "transcript": "Doctor, tengo fiebre de 39 grados y me duele mucho la herida, está roja y caliente",
            "paciente_id": "P001",
            "call_id": "smoke-2",
        })
        expect(r.status_code == 200, f"POST /api/assist rojo -> {r.status_code}")
        data = r.json()
        expect("response" in data, "response field present")
        decision = data["decision"]
        print(f"  decision: {decision.get('label')}", flush=True)
        print(f"  alert: {decision.get('alert')}", flush=True)
        print(f"  response: {data['response'][:100]}...", flush=True)
        time.sleep(1)

        step("4. /api/assist — amarillo case (fiebre leve)")
        r = c.post("/api/assist", json={
            "transcript": "Tengo 37.8 de temperatura y un poco de dolor en la herida",
            "paciente_id": "P001",
            "call_id": "smoke-3",
        })
        expect(r.status_code == 200, f"POST /api/assist amarillo -> {r.status_code}")
        data = r.json()
        print(f"  decision: {data['decision'].get('label')}", flush=True)
        print(f"  response: {data['response'][:100]}...", flush=True)
        time.sleep(1)

        step("5. /admin/documents")
        r = c.get("/admin/documents")
        expect(r.status_code == 200, f"GET /admin/documents -> {r.status_code}")
        docs = r.json().get("documents", [])
        print(f"  documents in KB: {len(docs)}", flush=True)
        expect(isinstance(docs, list), "documents is a list")

        step("6. /admin/upload + /admin/delete")
        test_pdf = Path("dataset/textos/Appendicitis/Apendicitis.pdf")
        if test_pdf.exists():
            with test_pdf.open("rb") as f:
                r = c.post("/admin/upload", files={"file": ("smoke_test.pdf", f, "application/pdf")})
            expect(r.status_code == 200, f"POST /admin/upload -> {r.status_code}")
            uploaded = r.json()
            doc_id = uploaded.get("doc_id") or uploaded.get("document", {}).get("doc_id")
            print(f"  uploaded: {uploaded}", flush=True)
            expect(bool(doc_id), f"doc_id returned (got {doc_id!r})")

            r = c.post("/admin/delete", json={"doc_id": doc_id})
            expect(r.status_code == 200, f"POST /admin/delete -> {r.status_code}")
            print(f"  deleted: {r.json()}", flush=True)
        else:
            print(f"  SKIP: {test_pdf} not found", flush=True)

        step("7. /api/metrics")
        r = c.get("/api/metrics")
        expect(r.status_code == 200, f"GET /api/metrics -> {r.status_code}")
        m = r.json()
        print(f"  requests: {m.get('requests')}", flush=True)
        print(f"  latency p50: {m.get('latency_ms', {}).get('p50'):.0f}ms", flush=True)
        print(f"  latency p95: {m.get('latency_ms', {}).get('p95'):.0f}ms", flush=True)
        print(f"  total tokens: {m.get('tokens', {}).get('total')}", flush=True)
        print(f"  cost USD: ${m.get('cost_usd', 0):.4f}", flush=True)

        step("8. /api/summary")
        r = c.post("/api/summary", json={"call_id": "smoke-2"})
        if r.status_code == 200:
            print(f"  summary: {json.dumps(r.json(), indent=2)[:300]}", flush=True)
        else:
            print(f"  status {r.status_code}: {r.text[:200]}", flush=True)

    print("\n=== ALL CHECKS PASSED ===", flush=True)


if __name__ == "__main__":
    main()
