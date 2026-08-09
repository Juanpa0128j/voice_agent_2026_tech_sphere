FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/backend/requirements.txt

# Pre-download BGE-M3 model during build (faster first request)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')" || true

COPY backend/ /app/backend/
COPY dataset/ /app/dataset/

ENV PYTHONUNBUFFERED=1
ENV RAG_PERSIST_DIR=/app/backend/chroma

# Index PDFs into ChromaDB at build time
RUN python backend/embedding_example.py --input-dir dataset/textos --chroma-dir backend/chroma || echo "WARN: indexing failed, will retry on startup"

EXPOSE 8000

# On startup: ensure index exists, then start server
CMD ["sh", "-c", "python backend/embedding_example.py --input-dir dataset/textos --chroma-dir backend/chroma 2>/dev/null; uvicorn backend.api_app:app --host 0.0.0.0 --port 8000"]
