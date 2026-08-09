Embedding experiment CI & local instructions

CI: use the 'Embedding Experiment' workflow (Actions -> Embedding Experiment -> Run workflow). It will create backend/output with embeddings.npy and metadata.json and attach them as an artifact.

Local (Docker):
- docker build -t vs-agent-backend -f backend/Dockerfile .
- docker run --rm -v "$(pwd)":/workspace -w /workspace vs-agent-backend python backend/embedding_example.py --input-dir dataset/textos --out-dir ./backend/output

Notes:
- The CI workflow installs only the runtime deps needed for embeddings to speed up the job. For full dev, use backend/requirements.txt.
