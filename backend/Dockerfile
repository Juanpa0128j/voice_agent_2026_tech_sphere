FROM python:3.10-slim
WORKDIR /workspace
COPY backend/requirements.txt ./backend/requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends build-essential git curl && \
    python -m pip install --upgrade pip setuptools wheel && \
    python -m pip install --no-cache-dir -r backend/requirements.txt && \
    apt-get remove -y build-essential && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

COPY backend /workspace/backend
CMD ["python","backend/embedding_example.py","--help"]
