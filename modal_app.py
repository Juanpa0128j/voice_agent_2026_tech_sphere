"""Modal deployment for the Voice Agent API.

Wraps the existing FastAPI app (backend.api_app:app) and serves it as a
Modal web endpoint. The frontend HTML/JS is bundled into the image and
served by the same FastAPI app via StaticFiles (mounted at /).

ChromaDB and uploaded PDFs persist on a Modal Volume so they survive
container restarts. Secrets (GROQ_API_KEY) come from the Modal secret
`voice-agent-secrets`.
"""
from __future__ import annotations

import os
from pathlib import Path

import modal

APP_NAME = "voice-agent"

# ---------------------------------------------------------------------------
# Modal app + image
# ---------------------------------------------------------------------------

app = modal.App(APP_NAME)

# Volume for persistent state (ChromaDB + uploaded PDFs)
chroma_volume = modal.Volume.from_name("voice-agent-chroma", create_if_missing=True)
uploads_volume = modal.Volume.from_name("voice-agent-uploads", create_if_missing=True)

CHROMA_MOUNT = "/vol/chroma"
UPLOADS_MOUNT = "/vol/uploads"

# NOTE: run `cd frontend-app && pnpm build` before `modal deploy` — this
# bakes frontend-app/dist/ into the image; admin.html still ships from the
# old frontend/ dir separately (see below), only index.html is replaced.
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("build-essential")
    .pip_install_from_requirements("backend/requirements.txt")
    .add_local_dir("backend", remote_path="/app/backend", copy=True)
    .add_local_dir("dataset", remote_path="/app/dataset", copy=True)
    .add_local_dir("frontend-app/dist", remote_path="/app/frontend", copy=True)
    .add_local_file("frontend/admin.html", remote_path="/app/frontend/admin.html", copy=True)
    .env(
        {
            "RAG_PERSIST_DIR": CHROMA_MOUNT,
            "ADMIN_UPLOAD_DIR": UPLOADS_MOUNT,
            "ADMIN_DATA_DIR": "/app/dataset/textos",
            "PYTHONPATH": "/app",
        }
    )
)


# ---------------------------------------------------------------------------
# ASGI web function
# ---------------------------------------------------------------------------


@app.function(
    image=image,
    volumes={
        CHROMA_MOUNT: chroma_volume,
        UPLOADS_MOUNT: uploads_volume,
    },
    secrets=[modal.Secret.from_name("voice-agent-secrets", required_keys=["GROQ_API_KEY"])],
    cpu=2.0,
    memory=4096,
    timeout=300,
    scaledown_window=180,
)
@modal.concurrent(max_inputs=4)
@modal.asgi_app(label="voice-agent")
def serve():
    """Serve the FastAPI app from backend.api_app:app."""
    from backend.api_app import app as fastapi_app
    return fastapi_app


