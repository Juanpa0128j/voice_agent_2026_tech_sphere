Architecture (high level)

- Frontend (static): /frontend/index.html — browser voice UI using Web Speech API (STT) and Web SpeechSynthesis (TTS) for demo. Deploy on Vercel or any static host.
- Admin console (static demo): /frontend/admin.html — uploads to /admin endpoints on backend.
- Backend: Python service (FastAPI) providing:
  - /admin/* endpoints to upload/delete/reindex documents (backend/api_app.py)
  - decision logic and provenance (backend/decision.py)
- Vector store: Qdrant or local FAISS (index produced from embeddings). CI demonstrates embedding extraction; user can push to Qdrant.
- Orchestration: GitHub Actions for embedding experiment; Dockerfile for reproducible dev environment.

Data flow (call):

1. Patient speaks (browser STT) -> transcript
2. App sends transcript to backend /api/assist (not implemented yet) which:
   a) retrieves top-k docs from vector DB using embeddings
   b) composes RAG prompt and calls LLM (locally or via HF/OpenAI depending on chosen model)
   c) returns answer + provenance (list of doc ids and excerpts)
3. Decision module (backend/decision.py) inspects transcript/structured answers and returns severity label and rationale; if alert, notify configured channel.

Notes & next steps:

- Implement /api/assist endpoint and LLM orchestration.
- Implement provenance storage and per-response trace logs.
- Add automated tests and CI for the API.
