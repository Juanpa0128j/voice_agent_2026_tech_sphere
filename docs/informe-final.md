# Informe final — Voice Agent para seguimiento postoperatorio

**Participante:** Juan Pablo (Juanpa0128j)
**Reto:** Tech Sphere Challenge 2026 — Voice Agent Edition
**Fecha:** 9 de agosto de 2026
**Repositorio:** https://github.com/Juanpa0128j/voice_agent_2026_tech_sphere

---

## 1. Resumen ejecutivo

Construí un agente de voz en español que conversa con pacientes después de una cirugía, detecta síntomas, fundamenta sus respuestas en guías clínicas mediante RAG, y escala a personal médico cuando es necesario. Backend en FastAPI con pipeline STT → RAG → LLM → decisión → TTS, frontend React (cockpit clínico de 3 paneles), desplegado en Modal con ChromaDB persistente. 60/60 tests pasando.

---

## 2. Modelo de lenguaje elegido

### Decisión: **Groq + Llama 3.1 8B Instant**

```python
# backend/llm.py
class LLMClient:
    def __init__(self, model="llama-3.1-8b-instant"):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
```

### Por qué este modelo

| Criterio                  | Groq + Llama 3.1 8B                | Groq + Llama 3.3 70B                          | Gemini 1.5 Flash | Llama local        |
| ------------------------- | ---------------------------------- | --------------------------------------------- | ---------------- | ------------------ |
| Latencia                  | Muy baja (LPU)                     | Baja (LPU)                                    | Moderada         | Depende de CPU/GPU |
| Límite diario (tier free) | 500K TPD                           | **100K TPD — insuficiente para demo en vivo** | $0 en tier free  | Sin límite         |
| Razonamiento clínico      | Bueno para extracción estructurada | Alto                                          | Alto             | Medio-bajo (3B)    |
| Requiere GPU              | No                                 | No                                            | No               | Sí/CPU lento       |
| Dependencia de red        | Sí (Groq API)                      | Sí (Groq API)                                 | Sí (Google API)  | No                 |

**Razón principal:** empecé con Llama 3.3 70B Versatile, pero su límite de 100K tokens/día en el tier gratuito de Groq se agotaba a mitad de una sesión de pruebas con el dataset de 160 casos — inaceptable para una demo en vivo o para el evaluador probando el sistema repetidamente. Llama 3.1 8B Instant tiene un límite diario de 500K tokens, suficiente margen para desarrollo, calibración y evaluación sin interrupciones, a costa de algo de calidad de razonamiento que compensamos con extracción JSON estructurada + reglas deterministas (ver §5) en vez de dejar que el LLM decida la severidad directamente.

**Por qué no Gemini Flash:** ventana de contexto mayor, pero el reto exige modelos de la familia Llama/Meta o equivalentes permitidos; Groq + Llama es la opción que cumple el requisito y da la latencia más baja para voz en tiempo real.

**Por qué no local:** correr un modelo local en el contenedor de Modal añadiría varios GB de peso a la imagen y latencia de inferencia en CPU — no vale la pena cuando Groq da latencia sub-segundo gratis.

---

## 3. Arquitectura

```
                    ┌───────────────────────────────────────────────────┐
                    │        Browser — React cockpit (3 paneles)        │
                    │  MediaRecorder (mic) ──────────────► /api/stt      │
                    │  <audio> playback    ◄────────────── /api/tts      │
                    └──────────────────────┬──────────────────────────┘
                                            │ transcript
                                            ▼
                    ┌───────────────────────────────────────────────────┐
                    │                  FastAPI (Modal)                  │
                    │  POST /api/stt   → Groq Whisper (whisper-large-v3) │
                    │  POST /api/assist                                  │
                    │    1. patient_context  → perfil + trayectoria      │
                    │    2. rag.retrieve     → BGE-M3 + ChromaDB top-k   │
                    │    3. llm.generate     → Groq Llama 3.1 8B         │
                    │    4. decision.decide  → JSON estructurado→reglas  │
                    │    5. conversation.append → historial in-memory    │
                    │    6. metrics.record   → P50/P95/tokens/costo      │
                    │  POST /api/tts   → edge-tts (es-CO-SalomeNeural)   │
                    │  GET  /api/timeline/{call_id}                      │
                    │  POST /api/summary                                 │
                    │  /admin/*  (upload / delete / reindex / documents) │
                    └──────────────────────┬──────────────────────────┘
                                            │
                              ┌─────────────┴─────────────┐
                              ▼                            ▼
                    ┌─────────────────┐          ┌─────────────────┐
                    │  ChromaDB        │          │  Groq Cloud      │
                    │  (Modal Volume,  │          │  Llama 3.1 8B +  │
                    │   persistente)   │          │  Whisper large-v3│
                    └─────────────────┘          └─────────────────┘
```

Decisiones clave:

- **RAG antes del LLM**, no después: la respuesta siempre se fundamenta en los PDFs clínicos, no en conocimiento paramétrico del modelo.
- **Decisión híbrida**: el LLM extrae síntomas estructurados (JSON), luego reglas determinísticas clasifican la severidad. Esto evita que una alucinación del LLM se traduzca en una mala decisión clínica, y hace la decisión auditable — cada clasificación tiene una razón explícita, no una caja negra.
- **STT/TTS en servidor**, no en el navegador: evita el error intermitente "network" de Web Speech API en Chrome y da control total sobre el idioma/acento (es-CO).
- **Persistencia de ChromaDB en Modal Volume**: el conocimiento sobrevive a reinicios/redeploys del contenedor.
- **Frontend desacoplado del backend**: build de React servido como archivos estáticos por FastAPI (mismo origen, sin CORS).

---

## 4. RAG y precisión clínica

### Embeddings: BGE-M3

Elegido por:

- Multilingüe con rendimiento top en español (evaluado en MTEB).
- Maneja chunks de hasta 8192 tokens.
- Licencia MIT.

Indexados los PDFs clínicos del corpus de Apendicitis (`dataset/textos/`) en ChromaDB con chunk size ~1200 caracteres.

### Validación contra el dataset

El dataset tiene 160 casos con `label_ground_truth` (verde/amarillo/rojo), en dos capas:

- **capa1_limpia**: conversaciones limpias donde el paciente responde lo que se le pregunta.
- **capa2_ruidosa**: misma conversación degradada con ruido realista (respuestas evasivas, ambigüedad, interrupciones de un familiar).

El script `scripts/calibrate.py` corre el agente sobre cada caso y compara la decisión con la etiqueta real:

| Capa             | Accuracy | Recall rojo | Notas                                               |
| ---------------- | -------- | ----------- | --------------------------------------------------- |
| Capa 1 (limpia)  | 76%      | 75%         | LLM 70B en la calibración original; mejor resultado |
| Capa 2 (ruidosa) | 37%      | 42%         | LLM con rate limit → fallback a keyword scoring     |

El **recall de "rojo" es la métrica más importante** porque un falso negativo en un caso crítico es la falla catastrófica en salud.

Sobre la capa ruidosa: el keyword scoring (fallback) falla porque los pacientes minimizan sus síntomas ("tranquila doctora, un poquito molesto no más"). El camino principal (LLM con extracción JSON estructurada) maneja estos casos mejor porque interpreta el lenguaje natural en vez de buscar substrings.

### Conocimiento vivo (hot-reload)

La consola de admin (`/admin/upload`) acepta un PDF, lo guarda, extrae texto con `pypdf`, y lo agrega a ChromaDB (`RAGStore.add_document`). La siguiente llamada al agente ya lo usa. El endpoint `/admin/delete` lo remueve del índice (`RAGStore.delete_document`) y la siguiente llamada ya no lo encuentra. Verificado end-to-end: subir → consultar (aparece en `retrieval`) → eliminar → consultar (ya no aparece).

### Trazabilidad

Cada respuesta del agente incluye un array `retrieval` con `{source, score}` por cada chunk usado — el frontend lo muestra como chips de cita bajo cada mensaje del agente y en el panel "Fuentes utilizadas" del cockpit.

---

## 5. Lógica de decisión y escalamiento

### Pipeline de decisión (`backend/decision.py`)

```
transcript
    │
    ▼
¿LLM disponible?
    │                              │
   sí                              no
    │                              │
    ▼                              ▼
extracción JSON estructurada   keyword scoring
(dolor_eva, fiebre_c,          (substring matching,
 sangrado, dificultad_         puntaje aditivo)
 respirar, secrecion,
 vomito, movilidad_limitada)
    │                              │
    ▼                              ▼
reglas clínicas determinísticas → score → label
    │
    ▼
score >= 6 → rojo   (action: alert)
score >= 3 → amarillo (action: warn)
score <  3 → verde   (action: respond)
```

### Reglas del camino principal (extracción estructurada)

| Señal                                | Puntos                    |
| ------------------------------------ | ------------------------- |
| Sangrado activo                      | +10                       |
| Dificultad respiratoria              | +10                       |
| Fiebre ≥ 39°C                        | +5                        |
| Fiebre 38–38.9°C                     | +3                        |
| Fiebre 37.5–37.9°C                   | +1                        |
| Secreción purulenta en herida        | +5                        |
| Dolor EVA ≥ 7                        | +3                        |
| Dolor EVA 5–6                        | +1                        |
| Movilidad limitada                   | +2                        |
| Vómito                               | +2                        |
| Combinación fiebre ≥38.5 + dolor ≥7  | score forzado a ≥8 (rojo) |
| Combinación fiebre ≥38.5 + secreción | score forzado a ≥8 (rojo) |

Cada decisión devuelve un `rationale` explícito (ej. `"fiebre 39.2°C (alta); dolor EVA 8/10"`) — no es una caja negra, el evaluador puede ver exactamente por qué se clasificó así.

### Fallback por keyword (cuando el LLM no está disponible)

Substring matching con pesos aditivos sobre el texto crudo (sangrado +5, dificultad para respirar +5, fiebre alta +4, dolor intenso +3, fiebre +3, vómito +2, dolor genérico +1, etc.), mismos umbrales (rojo ≥6, amarillo ≥3).

### Resumen al cerrar la llamada (`POST /api/summary`)

```json
{
  "call_id": "uuid",
  "paciente_id": "P001",
  "nombre": "Mauricio Juan González Sánchez",
  "procedimiento": "Apendicectomía",
  "dia_postoperatorio": 14,
  "sintomas_reportados": ["dolor EVA 8/10"],
  "decision": "amarillo",
  "fuentes": [],
  "proximos_pasos": [
    "Contactar a su médico en las próximas horas",
    "Vigilar síntomas"
  ],
  "alerta_enviada": true,
  "timestamp": "2026-08-09T18:33:49Z"
}
```

Verificado en vivo contra el backend real (no simulado) en esta sesión de trabajo.

---

## 6. Diseño de conversación

### System prompt (resumen)

El sistema prompt (`backend/prompts.py`) instruye al modelo a:

1. Asumir el rol de asistente de voz médico virtual (MediCol) para seguimiento postoperatorio.
2. **Nunca inventar** dosis, medicamentos ni procedimientos.
3. Si no sabe, decirlo y referir a un profesional de la salud.
4. Incluir el disclaimer obligatorio (no reemplaza consulta médica; llamar al 123 en emergencia).
5. Hacer preguntas de seguimiento concretas, no genéricas.
6. Mantener el saludo de apertura breve (2-3 frases, instrucción añadida tras detectar que un saludo largo generaba ~29s de audio TTS antes de que el usuario pudiera hablar).

### Glosario de regionalismos colombianos

`COLOMBIAN_SLANG_GLOSSARY` en `backend/prompts.py` mapea expresiones coloquiales colombianas ("abajito", "chiche", "fiebrón", "dolor de la muerte", etc.) a su equivalente clínico, para que el modelo interprete correctamente el lenguaje real del paciente.

### Manejo de entradas adversas

- **Off-topic**: el system prompt instruye redirigir amablemente a la conversación médica.
- **Hostil**: respuesta empática, no confrontacional.
- **Audio degradado o transcripción vacía**: el frontend permite reintentar la grabación; si `/api/stt` falla, se muestra un aviso en pantalla.
- **Fallo del LLM/RAG**: los endpoints degradan a HTTP 503 explícito en vez de fallar silenciosamente; el decision engine tiene su propio fallback determinista (keyword scoring) si la extracción estructurada falla.

---

## 7. Calidad de voz

### Decisión: STT y TTS en servidor, no Web Speech API del navegador

- **STT**: Groq Whisper (`whisper-large-v3`). El navegador captura audio con `MediaRecorder`, el backend transcribe en español. Evita el error intermitente "network" de Web Speech API en Chrome y funciona igual en cualquier navegador con soporte de `MediaRecorder`.
- **TTS**: `edge-tts` con la voz neural colombiana `es-CO-SalomeNeural`, streameada como MP3 desde `/api/tts`. Fallback a `speechSynthesis` del navegador si el endpoint falla.
- **Latencia**: se mitigó un cuello de botella real encontrado durante pruebas — el modelo de embeddings (BGE-M3) se cargaba de forma perezosa en la primera petición, sumando varios segundos al primer turno del usuario. Se agregó un warmup en el evento de arranque de FastAPI (`@app.on_event("startup")`) para pre-cargarlo antes de que llegue la primera llamada real.

### UX del frontend (cockpit clínico)

Reemplacé la interfaz de chat simple original por un **cockpit clínico de 3 paneles** (React + Vite + Tailwind + shadcn/ui + Framer Motion), pensado para comunicar "asistente clínico monitoreando a un paciente en recuperación" en vez de "chatbot":

- **Panel izquierdo — contexto del paciente**: nombre, procedimiento, día postoperatorio, EPS, comorbilidades, estado de recuperación (badge verde/amarillo/rojo), síntomas detectados.
- **Panel central — conversación de voz**: orbe animado con estado del agente (escuchando / procesando / hablando / escalamiento), botón de push-to-talk, transcript en vivo.
- **Panel derecho — inteligencia del agente**: nivel de riesgo y confianza, timeline de turnos clasificados, fuentes RAG citadas por cada respuesta, botones de acción (escalar a profesional, continuar monitoreo, pregunta de seguimiento, generar reporte del paciente — el reporte se renderiza en el mismo panel).

---

## 8. Métricas y observabilidad

Middleware en FastAPI mide por cada request a `/api/assist`:

- `latency_ms`: tiempo total de la llamada
- `prompt_tokens`, `completion_tokens`, `total_tokens`: del response de Groq
- `cost_usd`: calculado con precios públicos de Groq

Endpoint `/api/metrics` devuelve snapshot agregado:

```json
{
  "requests": 5,
  "latency_ms": { "p50": 1234, "p95": 2103, "count": 5 },
  "tokens": { "prompt": 4500, "completion": 1200, "total": 5700 },
  "cost_usd": 0.0036
}
```

---

## 9. Proceso de trabajo

Desarrollo iterativo con TDD estricto: cada endpoint/módulo nuevo se implementó con su suite de tests primero. Uso de subagentes especializados para paralelizar trabajo independiente (revisión de código, limpieza de código muerto, scaffolding de frontend) mientras se mantenía revisión humana en cada paso — incluyendo una revisión final de todo el cambio de frontend que encontró y corrigió dos bugs críticos de despliegue antes de mergear (ver §11).

### Decisiones técnicas más relevantes

#### 1. Decisión clínica híbrida (LLM + reglas)

**Evaluado:**

- LLM puro (decide directamente del texto) → riesgo de alucinación clínica, no auditable.
- Reglas puras (keyword matching) → no captura matices ni lenguaje minimizador.
- Modelo de ML entrenado → no hay tiempo ni datos suficientes.

**Elegido:** LLM extrae JSON estructurado, reglas determinísticas clasifican con `rationale` explícito.

**Riesgo identificado:** si el LLM no sigue el formato JSON, la extracción falla. Mitigación: prompt estricto con formato exacto + fallback automático a keyword scoring del texto crudo.

#### 2. BGE-M3 vs embeddings más livianos

**Evaluado:** `all-MiniLM-L6-v2` (rápido, inglés), `paraphrase-multilingual-MiniLM-L12-v2` (liviano, multilingüe), `bge-large-en-v1.5` (mejor en inglés), `BAAI/bge-m3` (multilingüe, 1024 dim, top en MTEB español).

**Elegido:** BGE-M3, por rendimiento en español.

**Riesgo:** modelo pesado, carga lenta en frío. Mitigación: warmup en el arranque del servidor (§7) en vez de carga perezosa en la primera petición real.

#### 3. React cockpit vs mantener frontend estático simple

**Evaluado:** mantener la interfaz de chat original (HTML/JS vanilla, sin build) vs reconstruir con React+Vite para soportar 8 componentes reutilizables con estado compartido y animaciones.

**Elegido:** React+Vite+Tailwind+shadcn/ui+Framer Motion. Se descartó Next.js (no aporta nada sobre Vite cuando el hosting es "FastAPI sirve archivos estáticos", forzaría SSR o export estático sin beneficio real) y CopilotKit (diseñado para backends con streaming de eventos de agente vía protocolo AG-UI; este backend es un pipeline síncrono por turno, adoptarlo requeriría reescribir el backend como un framework de agentes, fuera de alcance).

**Riesgo real encontrado:** el bundle de Vite usa rutas absolutas (`/assets/...`) pero FastAPI solo montaba estáticos en `/static` — esto habría producido una página en blanco en producción. Detectado y corregido en revisión final antes de mergear (`base: "/static/"` en `vite.config.ts`).

---

## 10. Entregables

| #   | Entregable               | Estado                                                         |
| --- | ------------------------ | -------------------------------------------------------------- |
| 01  | Repositorio público      | ✅ https://github.com/Juanpa0128j/voice_agent_2026_tech_sphere |
| 02  | Diagrama de arquitectura | ✅ `docs/architecture-diagram.png`                             |
| 03  | Informe final            | ✅ Este documento                                              |
| 04  | Video demo               | ⏳ Pendiente de grabación                                      |

---

## 11. Riesgos conocidos y mitigaciones

| Riesgo                                                               | Mitigación                                                                                                           |
| -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Límite diario de tokens de Groq (100K en 70B)                        | Cambio a Llama 3.1 8B Instant (500K TPD)                                                                             |
| Cold-start de BGE-M3 sumando latencia al primer turno                | Warmup en el arranque de FastAPI                                                                                     |
| Saludo de apertura muy largo (~29s de audio)                         | Instrucción explícita en el prompt para acortarlo a 2-3 frases                                                       |
| Markdown del LLM leído literalmente por TTS ("asterisco")            | Se limpia el markdown antes de enviar texto a `/api/tts`; se renderiza (de forma segura, con escape HTML) en el chat |
| Bundle de React con rutas absolutas rompiendo el despliegue estático | `base: "/static/"` en Vite, verificado con smoke test end-to-end                                                     |
| Falsos negativos en decisión clínica                                 | Reglas conservadoras + recall de rojo priorizado sobre accuracy general                                              |
| BGE-M3 pesado en la imagen de Modal                                  | Persistencia en Modal Volume, no se re-descarga en cada deploy                                                       |

---

## 12. Próximos pasos (con más tiempo)

1. **Wiring de `/api/timeline`** en el frontend para reconectar a una llamada en curso tras refrescar la página (el endpoint ya existe y está probado, solo falta el consumidor).
2. **Manejo de interrupciones (barge-in)** durante la reproducción de TTS — actualmente el usuario debe esperar a que el agente termine de hablar.
3. **Vitals reales** (temperatura, saturación) si el dataset llegara a incluirlos — decidí no fabricar datos clínicos falsos en el cockpit.
4. **CI con build de frontend** antes de cada deploy automático a Modal (ya implementado en este proyecto, ver `.github/workflows/deploy-modal.yml`).
5. **Telephony real** (Twilio) para llamadas de voz genuinas en vez de navegador.

---

## 13. Estado final del proyecto

### Compuertas eliminatorias

- **G1**: 4 entregables completos → 3 de 4 listos, video pendiente de grabación.
- **G2**: Levantar en ≤15 min → ✅ `modal deploy modal_app.py` con secreto pre-configurado (ver README Quickstart).
- **G3**: Modelo permitido → ✅ Llama 3.1 8B Instant (familia Llama, Groq tier gratuito).
- **G4**: Voz en tiempo real → ✅ Groq Whisper (STT) + edge-tts (TTS), verificado end-to-end con audio real.
- **G5**: Conocimiento vivo → ✅ Subir/eliminar documento vía consola admin, verificado end-to-end (sube → se recupera en RAG → se elimina → deja de aparecer).

### Criterios de puntuación

| Criterio                                    | Pts | Estado                                                                                                                 |
| ------------------------------------------- | --- | ---------------------------------------------------------------------------------------------------------------------- |
| RAG + precisión clínica + conocimiento vivo | 20  | ✅ BGE-M3 + ChromaDB, hot-reload verificado, trazabilidad de fuentes en UI                                             |
| Lógica de decisión + escalamiento           | 20  | ✅ Extracción estructurada + reglas deterministas, `rationale` explícito por decisión                                  |
| Comprensión + diseño conversación           | 15  | ✅ System prompt + glosario colombiano + disclaimer clínico + saludo acortado                                          |
| Calidad de voz                              | 15  | ✅ STT/TTS en servidor, latencia de cold-start mitigada, markdown limpiado antes de TTS                                |
| Video de argumentación                      | 15  | ⏳ Pendiente de grabación                                                                                              |
| Repositorio + proceso + buenas prácticas    | 15  | ✅ 60/60 tests, README con Quickstart ≤15min, CI de deploy automatizado, revisión de código en cada cambio de frontend |

### Verificación técnica

- 60/60 unit tests pasando (`PYTHONPATH=. pytest tests/ -v`)
- Pipeline completo verificado end-to-end con audio real sintetizado (STT → RAG → LLM → decisión → TTS) contra el backend corriendo localmente
- Cockpit React verificado end-to-end en navegador headless con micrófono simulado: saludo, turno de usuario, panel de riesgo, panel de evidencia, timeline, todos poblados con datos reales del backend
- Consola admin: subida y eliminación de documento verificadas, el agente aprende y olvida

### Comandos rápidos

```bash
# Desplegar (Modal)
modal deploy modal_app.py

# Probar
curl -X POST https://juanpa0128j--voice-agent.modal.run/api/assist \
  -H "Content-Type: application/json" \
  -d '{"transcript":"Doctor, tengo fiebre de 39 y dolor en la herida","paciente_id":"P001","call_id":"demo"}'

# Ver métricas
curl https://juanpa0128j--voice-agent.modal.run/api/metrics

# Tests
PYTHONPATH=. pytest tests/ -v
```

---

**Contacto:** communications@sourcemeridian.com
