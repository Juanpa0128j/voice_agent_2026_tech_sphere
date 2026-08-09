"""API scaffold: /api/assist endpoint for RAG retrieval (local FAISS fallback) and response provenance.
This is a minimal, runnable FastAPI app that uses embeddings.npy + metadata.json produced by the embedding experiment.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from pathlib import Path
import numpy as np
import json

app = FastAPI(title='Voice Agent API (skeleton)')
DATA_DIR = Path('backend/output')
EMB_FILE = DATA_DIR / 'embeddings.npy'
META_FILE = DATA_DIR / 'metadata.json'

class AssistRequest(BaseModel):
    transcript: str
    k: int = 3


def load_index():
    if not EMB_FILE.exists() or not META_FILE.exists():
        return None
    emb = np.load(EMB_FILE)
    with open(META_FILE,'r',encoding='utf-8') as f:
        meta = json.load(f)
    return emb, meta


@app.post('/api/assist')
async def assist(req: AssistRequest):
    """Return retrieved docs and a placeholder response.
    Real implementation: run reranker/LLM to produce final answer with provenance.
    """
    idx = load_index()
    if idx is None:
        raise HTTPException(status_code=503, detail='Embeddings not available. Run embedding experiment first (CI artifact or local).')
    emb, meta = idx
    # naive cosine search
    q = req.transcript.strip()
    if not q:
        raise HTTPException(status_code=400, detail='Empty transcript')
    # for safety, use a small local embedding using sentence-transformers if available
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        qv = model.encode([q], convert_to_numpy=True)[0]
    except Exception:
        # fallback: random vector (very rough)
        qv = np.random.randn(emb.shape[1])

    # cosine similarity
    def cosine(a,b):
        return float(np.dot(a,b) / (np.linalg.norm(a)*np.linalg.norm(b)+1e-8))
    scores = [cosine(qv, e) for e in emb]
    idxs = sorted(range(len(scores)), key=lambda i: -scores[i])[:req.k]
    results = []
    for i in idxs:
        results.append({'score': scores[i], 'meta': meta[i]})

    # placeholder response - in real flow send to LLM with retrieved contexts
    response_text = 'Respuesta provisional basada en documentos recuperados.'
    return {
        'response': response_text,
        'retrieval': results,
    }
