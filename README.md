# Voice Agent — Tech Sphere Challenge 2026

Agente de voz con IA para seguimiento postoperatorio. Construido para el [Tech Sphere Challenge 2026](https://sourcemeridian.com/tech-sphere-challenge).

## Quickstart (≤15 minutos)

### 1. Clonar y configurar

```bash
git clone https://github.com/Juanpa0128j/voice_agent_2026_tech_sphere.git
cd voice_agent_2026_tech_sphere
cp .env.example .env
# Editar .env y poner tu GROQ_API_KEY
```

### 2. Levantar con Docker

```bash
docker compose up --build
```

El backend queda en `http://localhost:8000`. Documentación OpenAPI en `http://localhost:8000/docs`.

### 3. Probar el agente

```bash
curl -X POST http://localhost:8000/api/assist \
  -H "Content-Type: application/json" \
  -d '{"transcript": "Doctor, me duele mucho la herida y tengo fiebre de 39 grados", "paciente_id": "P001", "call_id": "test-1"}'
```

### 4. Frontend de voz

Abrir `http://localhost:8000/frontend/index.html` en Chrome (requiere HTTPS o localhost para Web Speech API).

Para la consola de admin: `http://localhost:8000/frontend/admin.html`.

## Modelo de lenguaje

**Groq + Llama 3.3 70B Versatile** (`llama-3.3-70b-versatile`).

- **Por qué Groq**: latencia ultra-baja (LPU) — crítico para conversación de voz en tiempo real.
- **Por qué Llama 3.3 70B**: mejor razonamiento de la familia Llama, dentro del tier gratuito de Groq (30 RPM, 12K TPM, 1K RPD).
- **Alternativas evaluadas**: Gemini 1.5 Flash (ventana de contexto grande pero mayor latencia), Llama 3.2 3B local (más rápido pero menos capaz), Phi-3.5 local (sin latencia de red pero requiere GPU).

## Stack

| Componente | Tecnología | Detalle |
|---|---|---|
| LLM | Groq + Llama 3.3 70B | Tier gratuito, ~280 t/s |
| Embeddings | BGE-M3 (BAAI) | 1024 dim, multilingüe, 100+ idiomas |
| Vector DB | ChromaDB (PersistentClient) | Local, sin servidor |
| TTS / STT | Web Speech API (`es-CO`) | Sin dependencias, Chrome |
| Backend | FastAPI + Python 3.11 | Async, OpenAPI |
| Orquestación | Docker Compose | Un solo comando |

## Arquitectura

```
[Paciente] → (mic) → [Browser STT es-CO] → transcript
                                              ↓
                                   POST /api/assist
                                              ↓
              ┌────────────────────[ FastAPI ]────────────────────┐
              │  1. patient_context.py → carga perfil P001        │
              │  2. rag.py            → BGE-M3 + ChromaDB top-k  │
              │  3. prompts.py        → system prompt + glossary  │
              │  4. llm.py            → Groq Llama 3.3 70B        │
              │  5. decision.py       → LLM JSON → reglas → color │
              │  6. conversation.py   → siguiente pregunta        │
              │  7. summary.py        → resumen al cerrar         │
              │  8. metrics.py        → P50/P95/tokens/costo      │
              └────────────────────────────────────────────────────┘
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
| POST | `/api/assist` | Endpoint principal: recibe transcript, devuelve respuesta + decisión + fuentes |
| GET | `/api/metrics` | Métricas: P50/P95 latencia, tokens, costo estimado |
| POST | `/api/summary` | Resumen estructurado de una llamada cerrada |
| GET | `/admin/documents` | Lista de documentos en la base de conocimiento |
| POST | `/admin/upload` | Subir PDF, lo agrega a ChromaDB |
| POST | `/admin/delete` | Eliminar documento (ChromaDB) |
| POST | `/admin/reindex` | Re-indexar toda la base |

## Métricas (rubrica §5 — obligatorias)

Reportadas en `/api/metrics` después de cada llamada:

- **Latencia**: P50 y P95 desde que el paciente termina de hablar hasta que empieza a sonar el audio del agente.
- **Consumo**: tokens de entrada y salida por turno, invocaciones al modelo por turno, consultas al RAG por llamada.
- **Costo estimado por llamada**: basado en precios públicos de Groq (`$0.59/M input, $0.79/M output` para Llama 3.3 70B).

Para correr una demo y ver las métricas reales:

```bash
# Llamar al endpoint 5 veces con distintos transcripts
for i in 1 2 3 4 5; do
  curl -s -X POST http://localhost:8000/api/assist \
    -H "Content-Type: application/json" \
    -d "{\"transcript\": \"Tengo dolor $i de 10\", \"paciente_id\": \"P001\", \"call_id\": \"demo-$i\"}" > /dev/null
done

# Ver métricas
curl -s http://localhost:8000/api/metrics | python -m json.tool
```

## Tests

```bash
pip install -r backend/requirements.txt
pytest tests/ -v
```

**53/53 tests passing.** Cobertura: 80%+ en lógica clínica (`decision.py`, `summary.py`).

## Estructura

```
.
├── backend/
│   ├── api_app.py          # FastAPI endpoints
│   ├── admin_app.py        # Admin console endpoints
│   ├── patient_context.py  # Carga perfil del paciente desde el dataset
│   ├── prompts.py          # System prompt, glosario, few-shot
│   ├── rag.py              # BGE-M3 + ChromaDB
│   ├── llm.py              # Cliente Groq
│   ├── decision.py         # Clasificador de severidad
│   ├── conversation.py     # Flujo de conversación
│   ├── summary.py          # Resumen estructurado
│   ├── metrics.py          # P50/P95/tokens/costo
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── index.html          # UI de voz (STT + TTS)
│   └── admin.html          # Consola de conocimiento
├── dataset/                # Vendored from TechSphere2026/ParticipantArtifacts
│   ├── textos/             # 107 PDFs clínicos
│   ├── dataset_final.xlsx
│   ├── perfiles_*.xlsx
│   └── trayectorias_*.xlsx
├── docs/
│   ├── architecture.md
│   ├── architecture-diagram.png
│   ├── rubrica-evaluacion.md
│   ├── stack-tecnico.md
│   └── informe-final.md
├── tests/                  # 53 tests
├── docker-compose.yml
├── pytest.ini
├── .env.example
└── LICENSE
```

## Licencia

MIT — ver [`LICENSE`](LICENSE).
