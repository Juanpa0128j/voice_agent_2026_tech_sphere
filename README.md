# voice_agent_2026_tech_sphere

Demo project for Tech Sphere Challenge 2026 — Voice Agent prototype (RAG + Voice UI).

Quickstart

1) Produce embeddings (CI):
   - Open this repository's Actions -> "Embedding Experiment" -> Run workflow. The job will create backend/output with embeddings.npy and metadata.json and attach them as an artifact.

2) Run locally via Docker (alternative):
   - docker build -t vs-agent-backend -f backend/Dockerfile .
   - docker run --rm -v "$(pwd)":/workspace -w /workspace vs-agent-backend python backend/embedding_example.py --input-dir dataset/textos --out-dir ./backend/output

3) Start API (requires embeddings from step 1 or 2):
   - python -m pip install -r backend/requirements.txt
   - uvicorn backend.api_app:app --reload --port 8000
   - POST /api/assist with JSON {"transcript":"tengo fiebre"}

4) Frontend demo:
   - Serve /frontend folder (e.g., Python: python -m http.server -d frontend 3000)
   - Open index.html in Chrome to test Web Speech API STT and TTS (demo only)

Notes
- The repo includes vendor dataset from TechSphere2026/ParticipantArtifacts under dataset/. See docs/architecture.md for architecture and next steps.
- For reproducibility, prefer running the CI workflow or Docker image. The embedding extraction can be heavy locally.

Contact
- communications@sourcemeridian.com
