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

# NOTE: PDF indexing is NOT done at build time (would take ~90 min on CPU).
# The agent works without indexed PDFs; the LLM alone is sufficient for the demo.
# To enable RAG: docker compose run --rm backend python backend/embedding_example.py \
#   --input-dir dataset/textos --chroma-dir backend/chroma
# Or use the /admin/upload endpoint to add documents at runtime.

EXPOSE 8000

CMD ["uvicorn", "backend.api_app:app", "--host", "0.0.0.0", "--port", "8000"]
