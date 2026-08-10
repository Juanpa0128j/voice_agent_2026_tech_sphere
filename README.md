# Voice Agent — Tech Sphere Challenge 2026

Agente de voz con IA para seguimiento postoperatorio. Construido para el [Tech Sphere Challenge 2026](https://sourcemeridian.com/tech-sphere-challenge).

## Demo

- **Live demo (desplegado):** https://juanpa0128j--voice-agent.modal.run
- **Video demo (YouTube unlisted):** https://youtu.be/PLACEHOLDER
- **Diagrama de arquitectura:** [`docs/architecture-diagram.png`](docs/architecture-diagram.png)
- **Informe final:** [`docs/informe-final.md`](docs/informe-final.md)

> End-to-end verified: STT → RAG (BGE-M3 + ChromaDB) → LLM (Groq Llama 3.1 8B Instant) → decision (verde/amarillo/rojo) → TTS, con ChromaDB persistente en Modal Volume.

## Interacción de voz

El cockpit (`frontend-app/`, React + Vite) escucha por defecto — no hay botón de "hablar" ni de "confirmar":

1. Al abrir la llamada, el agente saluda automáticamente.
2. Cuando termina de hablar, el micrófono se activa solo.
3. Detección de silencio (~2.2s) por RMS decide cuándo terminaste de hablar y envía el turno automáticamente.
4. **Barge-in**: puedes interrumpir al agente mientras habla — el sistema detecta tu voz por encima de un umbral y corta la reproducción para escucharte.
5. El único control manual es un ícono de micrófono que silencia/pausa (deja de escuchar, pero el agente sigue hablando si ya estaba hablando) — no detiene toda la llamada.
6. **Escalamiento** a `rojo` es automático — no hay botón "escalar", el sistema lo hace y lo notifica.
7. "Finalizar llamada" detiene el ciclo de escucha y genera el resumen estructurado automáticamente.
8. Caption en vivo (best-effort, vía `SpeechRecognition` del navegador) — solo visual, el transcript real que usa el pipeline siempre viene de Groq Whisper.

## Modelo de lenguaje y voz (declaración explícita)

- **LLM**: Groq + Llama 3.1 8B Instant (`llama-3.1-8b-instant`) — familia Meta Llama,
  nivel gratuito de Groq. Default 3.3 70B excedía el límite TPD (100K tokens/día).
- **Voz STT**: Groq Whisper (`whisper-large-v3`) — captura por `MediaRecorder` en el
  navegador, detección de silencio con `AnalyserNode`, transcripción en español en el
  servidor. Sin dependencia de Web Speech API (evita el error "network" de Chrome).
- **Voz TTS**: edge-tts `es-CO-SalomeNeural` — voz neural colombiana natural, MP3
  streameado desde `/api/tts`. Fallback a `speechSynthesis` del navegador si el
  endpoint falla.
- **Embeddings**: BAAI/bge-m3 (1024 dim, multilingüe).
- **Vector DB**: ChromaDB PersistentClient, persistente en Modal Volume.

## Quickstart (≤15 min)

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

| Step                                                | What it does                      | Verified                                                   |
| --------------------------------------------------- | --------------------------------- | ---------------------------------------------------------- |
| `/api/health`                                       | Liveness probe                    | 200, ~0.7 s                                                |
| `/`                                                 | Serve `index.html`                | 200, 31 KB                                                 |
| `/admin`, `/admin.html`                             | Serve admin console               | 200                                                        |
| `POST /api/assist` (greeting)                       | Open the call, return agent intro | 200, 351-char Spanish response                             |
| `POST /api/assist` rojo                             | "fiebre 39 + dolor 9"             | `label=rojo`, `alert=true`, 3 RAG chunks                   |
| `POST /api/assist` verde                            | "me siento bien"                  | `label=verde`                                              |
| `POST /api/summary`                                 | Build summary from history        | 200, structured call summary                               |
| `GET /admin/documents`                              | List knowledge base               | 6 indexed docs (Appendicitis corpus)                       |
| `POST /admin/upload` + `query` + `delete` + `query` | G5 knowledge alive                | PASS — uploaded doc retrieved, then forgotten after delete |

## Stack

| Componente | Tecnología                        | Detalle                                                                 |
| ---------- | --------------------------------- | ----------------------------------------------------------------------- |
| LLM        | Groq + Llama 3.1 8B Instant       | Modelo permitido (Meta Llama vía Groq). Default 3.3 70B hit TPD limits. |
| Embeddings | BGE-M3 (BAAI)                     | 1024 dim, multilingüe, 100+ idiomas                                     |
| Vector DB  | ChromaDB (PersistentClient)       | Persistente en Modal Volume                                             |
| STT        | Groq Whisper (`whisper-large-v3`) | Server-side, forzado a `es`                                             |
| TTS        | edge-tts (`es-CO-SalomeNeural`)   | Streaming MP3, fallback a Web Speech API                                |
| Backend    | FastAPI + Python 3.11             | Async, OpenAPI en `/docs`                                               |
| Hosting    | Modal                             | $30/mo free credit, Volumes, scales to zero                             |

## Modelo de lenguaje

**Groq + Llama 3.1 8B Instant** (`llama-3.1-8b-instant`).

- **Por qué Groq**: latencia ultra-baja (LPU), crítico para conversación de voz en tiempo real.
- **Por qué Llama 3.1 8B**: pertenece a la familia Meta Llama (permitida en la rúbrica, §1 del stack técnico), corre en el nivel gratuito de Groq, y el modelo 3.3 70B excedía el límite TPD (100K tokens/día) durante la calibración. 8B Instant tiene 500K TPD y conserva latencia de primer dígito.
- **Por qué no local**: BGE-M3 + ChromaDB ya ocupan ~3 GB de RAM, y el frío de carga local de Llama 3.x 1B–3B no compensa el costo de red.
- **Modelo declarado**: `llama-3.1-8b-instant` (configurable vía `GROQ_MODEL`).

## Arquitectura

```
[Paciente] → (mic, MediaRecorder + AnalyserNode) → audio blob
                                              ↓
                                  POST /api/stt (Groq Whisper)
                                              ↓
                                         transcript
                                              ↓
                                  POST /api/assist
                                              ↓
            ┌──────────────────[ FastAPI ]──────────────────┐
            │  1. patient_context.py → carga perfil P001     │
            │  2. rag.py            → BGE-M3 + ChromaDB    │
            │  3. prompts.py        → system prompt + glosario│
            │  4. llm.py            → Groq Llama 3.1 8B      │
            │  5. decision.py       → LLM JSON → reglas      │
            │  6. conversation.py   → historial persistido   │
            │  7. summary.py        → resumen al cerrar      │
            │  8. metrics.py        → P50/P95/tokens/costo   │
            └───────────────────────────────────────────────┘
                                              ↓
                response (texto) + decision (verde/amarillo/rojo) + sources + patient
                                              ↓
                                  POST /api/tts (edge-tts)
                                              ↓
                           MP3 stream → (speaker) → [Paciente]
```

El cockpit escucha continuamente (silencio → auto-envío, sin botones de confirmar) y permite interrumpir al agente mientras habla (barge-in). Ver "Interacción de voz" arriba.

Diagrama detallado en [`docs/architecture-diagram.png`](docs/architecture-diagram.png).

## Endpoints

| Método | Path                      | Descripción                                                                                                                                                                                                     |
| ------ | ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GET    | `/api/health`             | Liveness probe                                                                                                                                                                                                  |
| POST   | `/api/assist`             | Endpoint principal. Acepta `{transcript, call_id?, k?, paciente_id?, greeting?}`; `greeting=true` con transcript vacío abre la llamada. Devuelve `patient` (contexto clínico) además de `decision`/`retrieval`. |
| GET    | `/api/metrics`            | P50/P95 latencia, tokens, costo estimado                                                                                                                                                                        |
| POST   | `/api/summary`            | Resumen estructurado de una llamada, con contexto real del paciente y fuentes RAG citadas                                                                                                                       |
| POST   | `/api/stt`                | Transcripción de audio (Whisper) — multipart file → `{text, language, duration_ms}`                                                                                                                             |
| POST   | `/api/tts`                | Síntesis de voz colombiana (edge-tts) — `{text}` → stream `audio/mpeg`                                                                                                                                          |
| GET    | `/api/timeline/{call_id}` | Historial turno-por-turno de una llamada (transcript/response/decision/retrieval)                                                                                                                               |
| GET    | `/api/source/{doc_id}`    | Sirve el archivo fuente real citado en `retrieval` (con guard contra path traversal)                                                                                                                            |
| GET    | `/admin/documents`        | Lista de documentos en la base de conocimiento                                                                                                                                                                  |
| POST   | `/admin/upload`           | Subir PDF/TXT/MD, lo agrega a ChromaDB                                                                                                                                                                          |
| POST   | `/admin/delete`           | Eliminar documento de ChromaDB                                                                                                                                                                                  |
| POST   | `/admin/reindex`          | Re-indexar todo `ADMIN_DATA_DIR`                                                                                                                                                                                |

## Métricas (rubrica §5)

Reportadas en `/api/metrics`, acumuladas sobre todas las llamadas al proceso (`backend/metrics.py`):

- **Latencia**: P50 y P95 de `/api/assist` (RAG + LLM + decisión; no incluye STT/TTS, que son endpoints separados).
- **Consumo**: tokens de entrada/salida acumulados, tomados del campo `usage` real de la respuesta de Groq (`llm.py`'s `last_usage`), no estimados.
- **Costo estimado**: `tokens_in/1M * $0.59 + tokens_out/1M * $0.79` (tarifas usadas en `metrics.py` para `llama-3.1-8b-instant`).

**Medición real** (3 llamadas consecutivas — saludo + 2 turnos, servidor local, 9 ago 2026):

```json
{
  "requests": 3,
  "latency_ms": { "p50": 1321, "p95": 1572, "count": 3 },
  "tokens": { "prompt": 3419, "completion": 373, "total": 3792 },
  "cost_usd": 0.002312
}
```

Reproducible: levanta el backend, haz 2-3 llamadas a `/api/assist`, y consulta `GET /api/metrics`.

Resultados de calibración sobre 160 casos ground-truth (ver `docs/informe-final.md`):

| Capa             | Accuracy | Recall rojo | Notas                                     |
| ---------------- | -------- | ----------- | ----------------------------------------- |
| Capa 1 (limpia)  | 76 %     | 75 %        | LLM 70B, mejor resultado                  |
| Capa 2 (ruidosa) | 37 %     | 42 %        | LLM 70B con rate limit → fallback keyword |

## Tests

```bash
.venv/bin/pip install -r backend/requirements.txt
PYTHONPATH=. .venv/bin/pytest tests/ -v
```

**69/69 tests passing.** Cobertura: 80 %+ en lógica clínica (`decision.py`, `summary.py`), más 7 tests de robustez Capa 2 ruidosa (`tests/test_noisy_capa2.py`) y 8 tests de voz (`tests/test_voice.py`). El frontend (`frontend-app/`) no tiene suite unitaria propia (sin framework de test instalado) — se verifica end-to-end con Playwright + micrófono simulado (`--use-fake-device-for-media-stream`) contra el backend real en cada cambio.

## Estructura

```
.
├── backend/
│   ├── api_app.py          # FastAPI endpoints (incl. admin) + static frontend mount
│   ├── patient_context.py  # Perfil clínico del paciente
│   ├── prompts.py          # System prompt, glosario, few-shot
│   ├── rag.py              # BGE-M3 + ChromaDB + reindex()
│   ├── llm.py              # Cliente Groq + retry/backoff
│   ├── decision.py         # Clasificador de severidad
│   ├── conversation.py     # Flujo de conversación
│   ├── summary.py          # Resumen estructurado
│   ├── metrics.py          # P50/P95/tokens/costo
│   └── requirements.txt
├── frontend-app/           # Cockpit clínico (React + Vite + Tailwind + shadcn/ui)
│   ├── src/
│   │   ├── App.tsx             # Layout de 3 paneles
│   │   ├── hooks/useVoiceCall.ts   # Escucha continua, silencio, barge-in, mute, fin de llamada
│   │   └── components/         # PatientCard, VoiceVisualizer, RiskAssessment, etc.
│   └── dist/                # Build servido por FastAPI en /static (ver modal_app.py)
├── frontend/
│   └── admin.html          # Consola de conocimiento (servida en /admin, sin cambios)
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
├── tests/                  # 69 tests
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
