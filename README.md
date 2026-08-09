---
title: Voice Agent — Post-op Follow-up
emoji: 🩺
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Spanish voice agent for post-op follow-up (Tech Sphere 2026)
---

# Voice Agent — Tech Sphere Challenge 2026

Agente de voz con IA para seguimiento postoperatorio. Construido para el [Tech Sphere Challenge 2026](https://sourcemeridian.com/tech-sphere-challenge).

> **Live demo on Modal:** https://juanpa0128j--voice-agent.modal.run
> End-to-end verified: STT → RAG (BGE-M3 + ChromaDB) → LLM (Groq Llama 3.1 8B Instant) → decision (verde/amarillo/rojo) → TTS, with persistent ChromaDB on a Modal Volume.

## Quickstart

### Option A — Modal (live demo, 1 command)

The fastest path. ~30 s for the first request (BGE-M3 download), then instant.

```bash
pip install modal
modal token new                                  # one-time: opens browser
modal secret create voice-agent-secrets GROQ_API_KEY=<your-key>
modal deploy modal_app.py
```

The CLI prints the public URL on the same `modal.run` domain shown above.
Hugging Face Spaces requires PRO for Docker now; Modal's $30/mo free credit
covers this workload (BGE-M3 + ChromaDB) comfortably.

### Option B — Local Docker

```bash
git clone https://github.com/Juanpa0128j/voice_agent_2026_tech_sphere.git
cd voice_agent_2026_tech_sphere
cp .env.example .env              # set GROQ_API_KEY
docker build -t voice-agent .
docker run --rm -p 7860:7860 --env-file .env voice-agent
```

Backend on `http://localhost:7860`. UI at `/`, admin at `/admin` and `/admin.html`.

> **Note:** the bundled `docker-compose.yml` was deprecated during the Modal
> migration; the root `Dockerfile` is the source of truth. To re-enable compose,
> point `build: { context: . }` at the root and remove the `dockerfile:` key.

### Quick API test

```bash
# 1. Saludo (greeting handshake)
curl -X POST https://juanpa0128j--voice-agent.modal.run/api/assist \
  -H "Content-Type: application/json" \
  -d '{"transcript":"","greeting":true,"call_id":"demo-1"}'

# 2. Caso rojo (fiebre 39 + dolor 9)
curl -X POST https://juanpa0128j--voice-agent.modal.run/api/assist \
  -H "Content-Type: application/json" \
  -d '{"transcript":"doctor tengo fiebre de 39 grados y dolor 9 de 10 en la herida","call_id":"demo-1"}'
```

## End-to-end verification

Everything below was tested against the live Modal deployment
(`juanpa0128j--voice-agent.modal.run`) on Aug 9, 2026:

| Step | What it does | Verified |
|---|---|---|
| `/api/health` | Liveness probe | 200, ~0.7 s |
| `/` | Serve `index.html` | 200, 31 KB |
| `/admin`, `/admin.html` | Serve admin console | 200 |
| `POST /api/assist` (greeting) | Open the call, return agent intro | 200, 351-char Spanish response |
| `POST /api/assist` rojo | "fiebre 39 + dolor 9" | `label=rojo`, `alert=true`, 3 RAG chunks |
| `POST /api/assist` verde | "me siento bien" | `label=verde` |
| `POST /api/summary` | Build summary from history | 200, structured call summary |
| `GET /admin/documents` | List knowledge base | 6 indexed docs (Appendicitis corpus) |
| `POST /admin/upload` + `query` + `delete` + `query` | G5 knowledge alive | PASS — uploaded doc retrieved, then forgotten after delete |

## Stack

| Componente | Tecnología | Detalle |
|---|---|---|
| LLM | Groq + Llama 3.1 8B Instant | Modelo permitido (Meta Llama vía Groq). Default 3.3 70B hit TPD limits. |
| Embeddings | BGE-M3 (BAAI) | 1024 dim, multilingüe, 100+ idiomas |
| Vector DB | ChromaDB (PersistentClient) | Persistente en Modal Volume |
| TTS / STT | Web Speech API (`es-CO`) | Browser-native, sin dependencias |
| Backend | FastAPI + Python 3.11 | Async, OpenAPI en `/docs` |
| Hosting | Modal | $30/mo free credit, Volumes, scales to zero |

## Modelo de lenguaje

**Groq + Llama 3.1 8B Instant** (`llama-3.1-8b-instant`).

- **Por qué Groq**: latencia ultra-baja (LPU), crítico para conversación de voz en tiempo real.
- **Por qué Llama 3.1 8B**: pertenece a la familia Meta Llama (permitida en la rúbrica, §1 del stack técnico), corre en el nivel gratuito de Groq, y el modelo 3.3 70B excedía el límite TPD (100K tokens/día) durante la calibración. 8B Instant tiene 500K TPD y conserva latencia de primer dígito.
- **Por qué no local**: BGE-M3 + ChromaDB ya ocupan ~3 GB de RAM, y el frío de carga local de Llama 3.x 1B–3B no compensa el costo de red.
- **Modelo declarado**: `llama-3.1-8b-instant` (configurable vía `GROQ_MODEL`).

## Arquitectura

```
[Paciente] → (mic) → [Browser STT es-CO] → transcript
                                              ↓
                                  POST /api/assist
                                              ↓
            ┌──────────────────[ FastAPI ]──────────────────┐
            │  1. patient_context.py → carga perfil P001     │
            │  2. rag.py            → BGE-M3 + ChromaDB    │
            │  3. prompts.py        → system prompt + glosario│
            │  4. llm.py            → Groq Llama 3.1 8B      │
            │  5. decision.py       → LLM JSON → reglas      │
            │  6. conversation.py   → siguiente pregunta     │
            │  7. summary.py        → resumen al cerrar      │
            │  8. metrics.py        → P50/P95/tokens/costo   │
            └───────────────────────────────────────────────┘
                                              ↓
                response (texto) + decision (verde/amarillo/rojo) + sources
                                              ↓
                           [Browser TTS es-CO] → (speaker) → [Paciente]
```

Diagrama detallado en [`docs/architecture-diagram.png`](docs/architecture-diagram.png).

## Endpoints

| Método | Path | Descripción |
|---|---|---|
| GET | `/api/health` | Liveness probe |
| POST | `/api/assist` | Endpoint principal. Acepta `{transcript, call_id?, k?, paciente_id?, greeting?}`; `greeting=true` con transcript vacío abre la llamada. |
| GET | `/api/metrics` | P50/P95 latencia, tokens, costo estimado |
| POST | `/api/summary` | Resumen estructurado de una llamada cerrada |
| GET | `/admin/documents` | Lista de documentos en la base de conocimiento |
| POST | `/admin/upload` | Subir PDF/TXT/MD, lo agrega a ChromaDB |
| POST | `/admin/delete` | Eliminar documento de ChromaDB |
| POST | `/admin/reindex` | Re-indexar todo `ADMIN_DATA_DIR` |

## Métricas (rubrica §5)

Reportadas en `/api/metrics` después de cada llamada:

- **Latencia**: P50 y P95 desde que el paciente termina de hablar hasta que empieza a sonar el audio del agente.
- **Consumo**: tokens de entrada y salida por turno, invocaciones al modelo por turno, consultas al RAG por llamada.
- **Costo estimado por llamada**: basado en precios públicos de Groq para `llama-3.1-8b-instant` ($0.05/M input, $0.08/M output, free tier).

Resultados de calibración sobre 160 casos ground-truth (ver `docs/informe-final.md`):

| Capa | Accuracy | Recall rojo | Notas |
|---|---|---|---|
| Capa 1 (limpia) | 76 % | 75 % | LLM 70B, mejor resultado |
| Capa 2 (ruidosa) | 37 % | 42 % | LLM 70B con rate limit → fallback keyword |

## Tests

```bash
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/pytest tests/ -v
```

**60/60 tests passing.** Cobertura: 80 %+ en lógica clínica (`decision.py`, `summary.py`), más 7 tests de robustez Capa 2 ruidosa (`tests/test_noisy_capa2.py`).

## Estructura

```
.
├── backend/
│   ├── api_app.py          # FastAPI endpoints + static frontend mount
│   ├── admin_app.py        # Admin console endpoints
│   ├── patient_context.py  # Perfil clínico del paciente
│   ├── prompts.py          # System prompt, glosario, few-shot
│   ├── rag.py              # BGE-M3 + ChromaDB + reindex()
│   ├── llm.py              # Cliente Groq + retry/backoff
│   ├── decision.py         # Clasificador de severidad
│   ├── conversation.py     # Flujo de conversación
│   ├── summary.py          # Resumen estructurado
│   ├── metrics.py          # P50/P95/tokens/costo
│   ├── embedding_example.py# Indexador CLI
│   └── requirements.txt
├── frontend/
│   ├── index.html          # UI de voz (STT + TTS)
│   └── admin.html          # Consola de conocimiento
├── dataset/                # Vendored from TechSphere2026/ParticipantArtifacts
│   ├── textos/             # 107 PDFs clínicos
│   ├── textos_uploaded/    # PDFs subidos en runtime (en Modal Volume)
│   ├── dataset_final.xlsx
│   ├── perfiles_*.xlsx
│   └── trayectorias_*.xlsx
├── docs/
│   ├── architecture.md
│   ├── architecture-diagram.png
│   ├── rubrica-evaluacion.md
│   ├── stack-tecnico.md
│   ├── informe-final.md
│   └── video-guion.md
├── tests/                  # 60 tests
├── scripts/                # calibrate.py, smoke_test.py
├── Dockerfile              # root: HF Spaces + Modal compatible
├── modal_app.py            # Modal deploy: @modal.asgi_app + Volumes
├── docker-compose.yml      # legacy
├── pytest.ini
├── .env.example
└── LICENSE
```

## Licencia

MIT — ver [`LICENSE`](LICENSE).
