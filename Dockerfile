FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps: build-essential only for source packages without wheels
# (chromadb has cffi wheel, sentence-transformers has torch wheel, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Non-root user (HF Spaces runs as UID 1000)
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

# Install Python deps (better layer cache)
COPY --chown=user backend/requirements.txt $HOME/app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r $HOME/app/backend/requirements.txt

# Copy source
COPY --chown=user backend/ $HOME/app/backend/
COPY --chown=user dataset/ $HOME/app/dataset/
COPY --chown=user frontend/ $HOME/app/frontend/

# Runtime dirs + HF Spaces port
ENV RAG_PERSIST_DIR=$HOME/app/backend/chroma \
    ADMIN_DATA_DIR=$HOME/app/dataset/textos \
    ADMIN_UPLOAD_DIR=$HOME/app/dataset/textos_uploaded \
    HF_HOME=$HOME/.cache/huggingface \
    PORT=7860

EXPOSE 7860

# BGE-M3 model (~2.2GB) is downloaded at startup instead of build time
# to keep build minutes low. First user request takes ~30s for the download,
# subsequent requests are fast.
RUN mkdir -p $HOME/.cache/huggingface && chown -R user:user $HOME/.cache

USER user

CMD ["sh", "-c", "uvicorn backend.api_app:app --host 0.0.0.0 --port ${PORT}"]
