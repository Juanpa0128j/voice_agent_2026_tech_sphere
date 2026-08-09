"""FastAPI application for the Voice Agent.

This module exposes the public HTTP API used by the voice-agent frontend
(``/api/health``, ``/api/assist``, ``/api/metrics``, ``/api/summary``) and the
admin console (``/admin/documents``, ``/admin/delete``, ``/admin/upload``,
``/admin/reindex``).

Optional internal modules (RAG store, LLM client, conversation/summary
services, metrics collector, etc.) are imported lazily and behind a
graceful-degradation layer: if a module is not present the corresponding
endpoint returns HTTP ``503`` with ``{"error": "Module <name> not available
yet"}`` instead of crashing at import time. This lets the application be
loaded by ``fastapi.testclient.TestClient`` even when the rest of the stack
is still being built in parallel.
"""
from __future__ import annotations

import logging
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

logger = logging.getLogger("voice_agent.api")


app = FastAPI(title="Voice Agent API")


# ---------------------------------------------------------------------------
# Static frontend (mounted at /)
# ---------------------------------------------------------------------------
# Serves frontend/index.html, frontend/admin.html and their assets so a
# single container (e.g. Hugging Face Space) can host both the API and the
# UI on the same origin — no CORS needed.

_FRONTEND_DIR = Path(
    os.environ.get(
        "FRONTEND_DIR",
        str(Path(__file__).resolve().parent.parent / "frontend"),
    )
)
if _FRONTEND_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(_FRONTEND_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    def _root_index() -> Any:
        index_path = _FRONTEND_DIR / "index.html"
        if index_path.is_file():
            from fastapi.responses import FileResponse
            return FileResponse(str(index_path))
        return {"status": "ok", "message": "Voice Agent API. UI not found."}

    @app.get("/index.html", include_in_schema=False)
    def _index_html() -> Any:
        index_path = _FRONTEND_DIR / "index.html"
        if index_path.is_file():
            from fastapi.responses import FileResponse
            return FileResponse(str(index_path))
        return {"error": "index.html not found"}

    @app.get("/favicon.ico", include_in_schema=False)
    def _favicon() -> Any:
        from fastapi.responses import Response
        return Response(status_code=204)

    @app.get("/admin", include_in_schema=False)
    @app.get("/admin/", include_in_schema=False)
    @app.get("/admin.html", include_in_schema=False)
    def _admin_index() -> Any:
        admin_path = _FRONTEND_DIR / "admin.html"
        if admin_path.is_file():
            from fastapi.responses import FileResponse
            return FileResponse(str(admin_path))
        return {"error": "admin.html not found"}


# ---------------------------------------------------------------------------
# Pydantic request/response models
# ---------------------------------------------------------------------------


class AssistRequest(BaseModel):
    """Body for ``POST /api/assist``."""

    transcript: str = Field(default="", description="Patient's spoken/typed utterance")
    call_id: Optional[str] = Field(
        default=None,
        description="Optional call/session id; a new one is generated when omitted",
    )
    k: int = Field(default=3, ge=1, le=20, description="Number of retrieved chunks")
    paciente_id: Optional[str] = Field(
        default=None,
        description="Optional patient id used to load clinical context",
    )
    greeting: bool = Field(
        default=False,
        description="When true the request is treated as a call-opening greeting; empty transcript is allowed",
    )


class AssistResponse(BaseModel):
    call_id: str
    transcript: str
    response: str
    decision: Dict[str, Any] = Field(default_factory=dict)
    retrieval: List[Dict[str, Any]] = Field(default_factory=list)
    patient: Optional[Dict[str, Any]] = None


class SummaryRequest(BaseModel):
    call_id: str = Field(..., description="Call/session id to summarize")


class DeleteRequest(BaseModel):
    doc_id: str = Field(..., description="Id of the document to delete")


# ---------------------------------------------------------------------------
# Lazy module accessors
# ---------------------------------------------------------------------------
#
# Each accessor returns the requested object on first call and caches the
# result.  When the import fails the accessor stores a sentinel so subsequent
# calls do not re-attempt the import and simply return ``None``.  Endpoints
# use the returned ``None`` to translate into HTTP 503 responses.


_UNAVAILABLE = object()
_rag_store: Any = None
_llm_client: Any = None
_decision_engine: Any = None
_conversation_store: Any = None
_summary_service: Any = None
_metrics_collector: Any = None
_patient_context: Any = None
_admin_store: Any = None
_stt_client: Any = None


def _safe_import(name: str) -> Any:
    """Import ``backend.<name>`` and return the module, or ``None`` on failure."""
    try:
        import importlib

        return importlib.import_module(f"backend.{name}")
    except Exception as exc:  # noqa: BLE001 - report any import failure
        logger.warning("Optional backend.%s unavailable: %s", name, exc)
        return None


def get_rag_store() -> Any:
    """Return the RAG store, building it lazily on first access."""
    global _rag_store
    if _rag_store is None:
        module = _safe_import("rag")
        if module is None:
            _rag_store = _UNAVAILABLE
            return None
        try:
            persist_dir = os.environ.get("RAG_PERSIST_DIR", "backend/chroma")
            _rag_store = module.RAGStore(persist_dir=persist_dir)
        except Exception as exc:  # noqa: BLE001
            logger.warning("RAGStore init failed: %s", exc)
            _rag_store = _UNAVAILABLE
    return _rag_store if _rag_store is not _UNAVAILABLE else None


def get_llm_client() -> Any:
    global _llm_client
    if _llm_client is None:
        module = _safe_import("llm")
        if module is None:
            _llm_client = _UNAVAILABLE
            return None
        try:
            _llm_client = module.LLMClient()
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLMClient init failed: %s", exc)
            _llm_client = _UNAVAILABLE
    return _llm_client if _llm_client is not _UNAVAILABLE else None


def get_decision_engine() -> Any:
    global _decision_engine
    if _decision_engine is None:
        module = _safe_import("decision")
        if module is None:
            _decision_engine = _UNAVAILABLE
            return None
        try:
            _decision_engine = module.DecisionEngine()
        except Exception as exc:  # noqa: BLE001
            logger.warning("DecisionEngine init failed: %s", exc)
            _decision_engine = _UNAVAILABLE
    return _decision_engine if _decision_engine is not _UNAVAILABLE else None


def get_conversation_store() -> Any:
    global _conversation_store
    if _conversation_store is None:
        module = _safe_import("conversation")
        if module is None:
            _conversation_store = _UNAVAILABLE
            return None
        try:
            _conversation_store = module.ConversationStore()
        except Exception as exc:  # noqa: BLE001
            logger.warning("ConversationStore init failed: %s", exc)
            _conversation_store = _UNAVAILABLE
    return _conversation_store if _conversation_store is not _UNAVAILABLE else None


def get_summary_service() -> Any:
    global _summary_service
    if _summary_service is None:
        module = _safe_import("summary")
        if module is None:
            _summary_service = _UNAVAILABLE
            return None
        try:
            _summary_service = module.SummaryService()
        except Exception as exc:  # noqa: BLE001
            logger.warning("SummaryService init failed: %s", exc)
            _summary_service = _UNAVAILABLE
    return _summary_service if _summary_service is not _UNAVAILABLE else None


def get_metrics_collector() -> Any:
    global _metrics_collector
    if _metrics_collector is None:
        module = _safe_import("metrics")
        if module is None:
            _metrics_collector = _UNAVAILABLE
            return None
        try:
            _metrics_collector = module.MetricsCollector()
        except Exception as exc:  # noqa: BLE001
            logger.warning("MetricsCollector init failed: %s", exc)
            _metrics_collector = _UNAVAILABLE
    return _metrics_collector if _metrics_collector is not _UNAVAILABLE else None


def get_patient_context() -> Any:
    global _patient_context
    if _patient_context is None:
        module = _safe_import("patient_context")
        if module is None:
            _patient_context = _UNAVAILABLE
            return None
        try:
            _patient_context = module.PatientContext()
        except Exception as exc:  # noqa: BLE001
            logger.warning("PatientContext init failed: %s", exc)
            _patient_context = _UNAVAILABLE
    return _patient_context if _patient_context is not _UNAVAILABLE else None


def get_admin_store() -> Any:
    """Resolve the admin-side document store (RAG or filesystem fallback)."""
    global _admin_store
    if _admin_store is None:
        store = get_rag_store()
        if store is not None and store is not _UNAVAILABLE:
            _admin_store = store
            return _admin_store
        _admin_store = _UNAVAILABLE
    return _admin_store if _admin_store is not _UNAVAILABLE else None


def get_stt_client() -> Any:
    global _stt_client
    if _stt_client is None:
        module = _safe_import("stt")
        if module is None:
            _stt_client = _UNAVAILABLE
            return None
        try:
            _stt_client = module.STTClient()
        except Exception as exc:  # noqa: BLE001
            logger.warning("STTClient init failed: %s", exc)
            _stt_client = _UNAVAILABLE
    return _stt_client if _stt_client is not _UNAVAILABLE else None


def _module_unavailable_response(module_name: str) -> Dict[str, str]:
    return {"error": f"Module {module_name} not available yet"}


@app.on_event("startup")
async def _warm_rag_store() -> None:
    """Pre-load the RAG store (embedding model) so the first real request
    isn't slowed by a cold model load. Skipped under pytest so the test
    suite doesn't eat the embedding-model load on every run.
    """
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    try:
        get_rag_store()
    except Exception as exc:  # noqa: BLE001
        logger.warning("RAG warmup failed: %s", exc)


# ---------------------------------------------------------------------------
# /api endpoints
# ---------------------------------------------------------------------------


@app.get("/api/health")
def health() -> Dict[str, str]:
    """Liveness probe: always returns 200 ``{"status": "ok"}``."""
    return {"status": "ok"}


@app.post("/api/assist", response_model=AssistResponse)
async def assist(req: AssistRequest) -> Dict[str, Any]:
    """Main agent endpoint.

    Accepts a ``transcript`` and returns a synthesized response along with
    retrieval provenance and the routing decision.  When ``greeting`` is
    true an empty transcript is allowed and the response is the
    call-opening greeting; otherwise empty transcripts are rejected with
    HTTP 400.  When optional modules (RAG, LLM, decision engine,
    conversation store) are not yet wired, the endpoint returns HTTP 503.
    """
    transcript = (req.transcript or "").strip()
    is_greeting = bool(req.greeting) and not transcript

    if not transcript and not is_greeting:
        raise HTTPException(status_code=400, detail="Empty transcript")

    call_id = req.call_id or uuid.uuid4().hex
    started = time.perf_counter()

    rag = get_rag_store()
    llm = get_llm_client()
    decision = get_decision_engine()
    conversation = get_conversation_store()
    metrics = get_metrics_collector()

    if rag is None or llm is None or decision is None:
        missing = [
            name
            for name, obj in (
                ("rag", rag),
                ("llm", llm),
                ("decision", decision),
            )
            if obj is None
        ]
        return JSONResponse(
            status_code=503,
            content=_module_unavailable_response(", ".join(missing)),
        )

    retrieval: List[Dict[str, Any]] = []
    if not is_greeting:
        try:
            retrieval = list(rag.retrieve(transcript, k=req.k) or [])
        except Exception as exc:  # noqa: BLE001 - return 503 on retrieval failure
            logger.warning("RAG retrieve failed: %s", exc)
            return JSONResponse(
                status_code=503,
                content=_module_unavailable_response("rag"),
            )

    context = "\n\n".join(str(item.get("text", "")) for item in retrieval)

    # Conversation memory: prior turns make the agent adapt to what the
    # patient already said (symptoms, procedure, answers given).
    history: List[Dict[str, Any]] = []
    if conversation is not None:
        try:
            history = conversation.history(call_id)
        except Exception:
            history = []

    try:
        response_text = llm.generate(
            transcript=transcript, context=context, history=history[-6:]
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM generate failed: %s", exc)
        return JSONResponse(
            status_code=503,
            content=_module_unavailable_response("llm"),
        )

    try:
        decision_payload = decision.decide(transcript, retrieval, response_text)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Decision engine failed: %s", exc)
        decision_payload = {"action": "respond", "reason": "fallback"}

    patient_payload: Optional[Dict[str, Any]] = None
    if req.paciente_id:
        try:
            from backend.patient_context import load_patient_context
            ctx = load_patient_context(req.paciente_id)
            if ctx is not None:
                patient_payload = {
                    "paciente_id": ctx.paciente_id,
                    "nombre": ctx.nombre,
                    "procedimiento": ctx.procedimiento,
                    "dia_postoperatorio": ctx.dia_postoperatorio,
                    "comorbilidades": ctx.comorbilidades,
                    "eps": ctx.eps,
                }
        except Exception as exc:  # noqa: BLE001
            logger.warning("patient_context load failed: %s", exc)

    if conversation is not None and not is_greeting:
        try:
            conversation.append(call_id, transcript, response_text, decision_payload)
        except Exception as exc:  # noqa: BLE001
            logger.debug("ConversationStore append failed: %s", exc)

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if metrics is not None:
        try:
            metrics.record("assist", latency_ms=elapsed_ms, ok=True)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Metrics record failed: %s", exc)

    return {
        "call_id": call_id,
        "transcript": transcript,
        "response": response_text,
        "decision": decision_payload,
        "retrieval": retrieval,
        "patient": patient_payload,
    }


@app.get("/api/metrics")
def metrics() -> Dict[str, Any]:
    """Return collected metrics. Always returns 200 with at least an empty
    payload; the real P50/P95 latencies, token usage and cost come from
    ``backend.metrics`` when it is available.
    """
    collector = get_metrics_collector()
    if collector is None:
        return {
            "requests": 0,
            "latency_ms": {"p50": 0, "p95": 0, "count": 0},
            "tokens": {"prompt": 0, "completion": 0, "total": 0},
            "cost_usd": 0.0,
        }
    try:
        snapshot = collector.snapshot()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Metrics snapshot failed: %s", exc)
        return {"error": "metrics collection failed", "detail": str(exc)}
    return snapshot


@app.post("/api/summary")
async def get_summary(req: SummaryRequest) -> Dict[str, Any]:
    """Return the final summary for ``req.call_id``.

    Builds the summary from the conversation history if no saved summary exists.
    """
    service = get_summary_service()
    if service is None:
        return JSONResponse(
            status_code=503,
            content=_module_unavailable_response("summary"),
        )
    try:
        return service.summarize(req.call_id)
    except KeyError:
        # No saved summary — try to build one from conversation history
        conv = get_conversation_store()
        if conv is None:
            raise HTTPException(status_code=404, detail="call_id not found")
        history = conv.history(req.call_id)
        if not history:
            raise HTTPException(status_code=404, detail="call_id not found")
        from backend.summary import generate_summary, CallSummary
        from datetime import datetime, timezone
        turns = []
        for h in history:
            turns.append({"role": "user", "content": h.get("transcript", "")})
            turns.append({"role": "assistant", "content": h.get("response", "")})
        decision = history[-1].get("decision", {}) if history else {}
        summary = generate_summary(
            paciente_id="unknown",
            nombre="",
            procedimiento="",
            dia_postoperatorio=0,
            turns=turns,
            decision=decision,
            sources=[],
        )
        summary["call_id"] = req.call_id
        summary["timestamp"] = datetime.now(timezone.utc).isoformat()
        summary["duracion"] = "—"
        summary["mensajes"] = len(turns)
        service.save(summary)
        return summary
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("Summary failed: %s", exc)
        return JSONResponse(
            status_code=503,
            content=_module_unavailable_response("summary"),
        )


@app.get("/api/timeline/{call_id}")
def get_timeline(call_id: str) -> Dict[str, Any]:
    """Return the turn-by-turn history for a call (transcript/response/decision)."""
    conversation = get_conversation_store()
    if conversation is None:
        raise HTTPException(status_code=404, detail="call_id not found")
    turns = conversation.history(call_id)
    if not turns:
        raise HTTPException(status_code=404, detail="call_id not found")
    return {"call_id": call_id, "turns": turns}


# ---------------------------------------------------------------------------
# /api/stt and /api/tts — voice pipeline
# ---------------------------------------------------------------------------


_STT_ALLOWED_SUFFIXES = {".webm", ".ogg", ".mp3", ".wav", ".m4a"}


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


@app.post("/api/stt")
async def stt_endpoint(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Transcribe an audio blob (webm/ogg/mp3/wav/m4a) via Groq Whisper."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in _STT_ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail=f"Unsupported audio type: {suffix}")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio body")

    client = get_stt_client()
    if client is None:
        return JSONResponse(status_code=503, content=_module_unavailable_response("stt"))

    started = time.perf_counter()
    try:
        text = client.transcribe(file.filename, data)
    except Exception as exc:  # noqa: BLE001
        logger.warning("STT transcribe failed: %s", exc)
        return JSONResponse(status_code=503, content=_module_unavailable_response("stt"))

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return {"text": text, "language": "es", "duration_ms": round(elapsed_ms, 1)}


@app.post("/api/tts")
async def tts_endpoint(req: TTSRequest) -> Any:
    """Synthesize Colombian Spanish neural voice (edge-tts) as MP3 stream."""
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")

    from fastapi.responses import StreamingResponse

    try:
        module = _safe_import("tts")
        if module is None:
            raise RuntimeError("tts module unavailable")

        async def _gen():
            async for chunk in module.stream_tts(text):
                yield chunk

        return StreamingResponse(_gen(), media_type="audio/mpeg")
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("TTS failed: %s", exc)
        return JSONResponse(status_code=503, content=_module_unavailable_response("tts"))


# ---------------------------------------------------------------------------
# /admin endpoints
# ---------------------------------------------------------------------------


DATA_DIR = Path(os.environ.get("ADMIN_DATA_DIR", "dataset/textos"))
UPLOAD_DIR = Path(os.environ.get("ADMIN_UPLOAD_DIR", "dataset/textos_uploaded"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _scan_filesystem_documents() -> List[Dict[str, Any]]:
    """Fallback listing when the RAG store does not expose ``list``."""
    documents: List[Dict[str, Any]] = []
    for path in sorted(DATA_DIR.glob("**/*")):
        if path.is_file():
            documents.append(
                {
                    "doc_id": str(path.relative_to(DATA_DIR)),
                    "source": str(path),
                    "name": path.name,
                }
            )
    for path in sorted(UPLOAD_DIR.glob("**/*")):
        if path.is_file():
            documents.append(
                {
                    "doc_id": f"uploaded/{path.relative_to(UPLOAD_DIR)}",
                    "source": str(path),
                    "name": path.name,
                }
            )
    return documents


@app.get("/admin/index/status")
def index_status() -> Dict[str, Any]:
    """Return the state of the vector index for the admin console pill.

    Shape: ``{"n_documents": int, "n_chunks": int, "last_reindex": str|None}``.
    """
    store = get_admin_store()
    if store is None:
        return {"n_documents": 0, "n_chunks": 0, "last_reindex": None}
    try:
        docs = store.list_documents()
        n_docs = len(docs)
        n_chunks = 0
        try:
            n_chunks = store._collection.count()
        except Exception:
            n_chunks = 0
        last = None
        state_file = Path(os.environ.get("RAG_PERSIST_DIR", "backend/chroma")) / "chroma.sqlite3"
        if state_file.is_file():
            from datetime import datetime, timezone
            last = datetime.fromtimestamp(state_file.stat().st_mtime, tz=timezone.utc).isoformat()
        return {"n_documents": n_docs, "n_chunks": n_chunks, "last_reindex": last}
    except Exception as exc:  # noqa: BLE001
        return {"n_documents": 0, "n_chunks": 0, "last_reindex": None, "error": str(exc)}


@app.get("/admin/documents")
def list_documents() -> Dict[str, Any]:
    """List all documents in the knowledge base.  When the RAG store
    is available the listing comes from there, otherwise a filesystem
    scan over the dataset directories is used as a graceful fallback.
    """
    store = get_admin_store()
    if store is not None:
        try:
            docs = store.list_documents()
            return {"documents": list(docs)}
        except Exception as exc:  # noqa: BLE001
            logger.warning("RAG list_documents failed, falling back: %s", exc)
    return {"documents": _scan_filesystem_documents()}


@app.post("/admin/delete")
async def delete_document(req: DeleteRequest) -> Dict[str, Any]:
    """Delete a document by id. Returns 200 when the store accepts the
    delete (even if no row existed) and 404 when the id was not present in
    either the RAG store or the filesystem fallback.
    """
    store = get_admin_store()
    if store is not None:
        try:
            deleted = store.delete_document(req.doc_id)
            if deleted:
                return {"ok": True, "doc_id": req.doc_id}
            raise HTTPException(status_code=404, detail="doc_id not found")
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("RAG delete failed: %s", exc)

    candidate = None
    for root in (DATA_DIR, UPLOAD_DIR):
        candidate = root / req.doc_id
        if not candidate.exists():
            try:
                candidate = root / Path(req.doc_id).name
            except Exception:
                candidate = None
        if candidate is not None and candidate.exists():
            try:
                candidate.unlink()
                return {"ok": True, "doc_id": req.doc_id}
            except OSError as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc
    raise HTTPException(status_code=404, detail="doc_id not found")


@app.post("/admin/upload")
async def upload_document(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Upload a PDF (or text) document, persist it on disk, and trigger a
    re-index into the RAG store when available.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".pdf", ".txt", ".md"}:
        raise HTTPException(status_code=400, detail="Only PDF/TXT/MD allowed")

    target = UPLOAD_DIR / file.filename
    counter = 1
    while target.exists():
        target = UPLOAD_DIR / f"{Path(file.filename).stem}_{counter}{suffix}"
        counter += 1

    with target.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    text: Optional[str] = None
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(target))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as exc:  # noqa: BLE001
            logger.warning("PDF extraction failed for %s: %s", target, exc)
    else:
        try:
            text = target.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Text read failed for %s: %s", target, exc)

    store = get_rag_store()
    indexed = False
    if store is not None and text:
        try:
            doc_id = store.add_document(
                doc_id=target.relative_to(UPLOAD_DIR).as_posix(),
                text=text,
                metadata={"source": str(target), "filename": file.filename},
            )
            indexed = True
            return {"ok": True, "doc_id": doc_id, "indexed": True}
        except Exception as exc:  # noqa: BLE001
            logger.warning("RAG add_document failed: %s", exc)

    return {
        "ok": True,
        "doc_id": target.relative_to(UPLOAD_DIR).as_posix(),
        "indexed": indexed,
        "path": str(target),
    }


@app.post("/admin/reindex")
async def reindex() -> Dict[str, Any]:
    """Trigger a full reindex of every document on disk."""
    store = get_rag_store()
    if store is None:
        return JSONResponse(
            status_code=503,
            content=_module_unavailable_response("rag"),
        )
    try:
        result = store.reindex()
        return {"ok": True, "result": result}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Reindex failed: %s", exc)
        return JSONResponse(
            status_code=503,
            content=_module_unavailable_response("rag"),
        )


__all__ = ["app"]
