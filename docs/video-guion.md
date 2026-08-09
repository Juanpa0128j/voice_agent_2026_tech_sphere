# Video Demo — Tech Sphere Challenge 2026

## Overview

- **Duración**: 3-5 minutos
- **Formato**: Screen recording + face cam para las 2 preguntas finales
- **Publicación**: YouTube unlisted (no aparece en búsquedas ni en tu canal)
- **Herramientas**: OBS Studio (gratis) o Loom
- **Live URL**: https://juanpa0128j--voice-agent.modal.run
- **Repo**: https://github.com/Juanpa0128j/voice_agent_2026_tech_sphere

> Si tu navegador falla con Web Speech API ("network error"), usa el **fallback de
> texto** que aparece debajo del botón de micrófono: es la misma API, solo
> tecleas en vez de hablar. Esto NO es trampa, es lo que el agente espera.

---

## Pre-flight check (corre esto antes de grabar)

```bash
# 1. Health
curl -sS https://juanpa0128j--voice-agent.modal.run/api/health
# esperado: {"status":"ok"}

# 2. UI
curl -sS -o /dev/null -w "%{http_code}\n" https://juanpa0128j--voice-agent.modal.run/
# esperado: 200
curl -sS -o /dev/null -w "%{http_code}\n" https://juanpa0128j--voice-agent.modal.run/admin.html
# esperado: 200

# 3. RAG retrieval
curl -sS -X POST https://juanpa0128j--voice-agent.modal.run/api/assist \
  -H "Content-Type: application/json" \
  -d '{"transcript":"fiebre despues de apendicitis","call_id":"preflight-1"}' \
  | python -m json.tool | head -30
# esperado: retrieval_count >= 1, sources contienen "Appendicitis/..."
```

Si el primer `/api/assist` tarda ~30s, es la descarga de BGE-M3 en cold start.
Los siguientes son instantáneos.

---

## Estructura del video

### Parte 1: Demo funcional (2-3 min)

**0:00-0:20 — Apertura**
- Mostrar el repo en GitHub: https://github.com/Juanpa0128j/voice_agent_2026_tech_sphere
- Señalar: LICENSE MIT, README con tabla de verificación e2e, 60/60 tests pasando
- "Esto es un agente de voz con IA para seguimiento postoperatorio, desplegado
  en Modal y accesible en juanpa0128j--voice-agent.modal.run"

**0:20-0:50 — Stack y decisiones**
- Mencionar: Groq + Llama 3.1 8B Instant, BGE-M3 + ChromaDB, Web Speech API es-CO
- "Stack 100% nivel gratuito, sin costo de operación, con persistencia
  real (Modal Volume)"

**0:50-1:30 — Demo de voz end-to-end**
- Abrir https://juanpa0128j--voice-agent.modal.run/ en Chrome
- Click en "Iniciar Llamada"
- Hablar (o leer el guion abajo):
  1. "Hola"
  2. "Me operaron del apéndice hace tres días"
  3. "Tengo dolor como 7 de 10"
  4. "Sí tengo fiebre, como 38.5"
  5. "La herida está un poco roja"
- El agente debe:
  - Responder con voz (TTS) en español
  - Mostrar el badge de decisión subiendo: verde → amarillo → **ROJO** (fiebre + herida roja + dolor alto)
  - Alertar al final

**1:30-2:00 — Conocimiento vivo (G5)**
- Abrir https://juanpa0128j--voice-agent.modal.run/admin.html en otra pestaña
- Mostrar la lista de 6 documentos ya indexados (corpus Appendicitis)
- Subir un PDF de prueba (puede ser cualquier PDF clínico — un par de párrafos basta)
- Verificar que aparece con badge "indexed: true"
- Volver a la pestaña de la llamada, hacer una pregunta que requiera ese documento
- Mostrar la cita verificable en `retrieval` (sources, score)
- Eliminar el documento, hacer la misma pregunta, mostrar que la respuesta ya no
  tiene la fuente

**2:00-2:30 — Métricas**
- En terminal: `curl -s https://juanpa0128j--voice-agent.modal.run/api/metrics | python -m json.tool`
- Mostrar P50/P95, tokens, costo estimado
- Mencionar: ~$0.0002 por llamada típica en 8B Instant (free tier)

**2:30-3:00 — Finalizar y resumen**
- Click en "Finalizar Llamada" → modal de resumen estructurado
- Mostrar: paciente, decisión final, síntomas, próximos pasos

### Parte 2: Preguntas frente a cámara (1-2 min)

**3:00-4:00 — Pregunta 1: Valor diferencial**

> "Si debes convencer a un cliente de que adopte el agente que construiste,
> ¿cómo presentarías el problema que resuelve, por qué tu solución es la
> adecuada y qué valor diferencial ofrece frente a otras alternativas?"

**Puntos sugeridos** (NO los leas, úsalos como guía mental):
- **Problema**: el seguimiento postoperatorio hoy depende de personal humano,
  es costoso, no escala, y está sujeto a errores de comunicación y cansancio.
- **Por qué mi solución**: combina IA conversacional con RAG clínico
  fundamentado, decisión automatizada con escalamiento por reglas, y
  conocimiento vivo (la consola permite actualizar las guías en caliente sin
  reentrenar nada).
- **Valor diferencial vs alternativas**:
  - vs chatbot genérico: cada respuesta clínica es **citada** y verificable
  - vs call center humano: 24/7, escala infinita, costo marginal ~$0
  - vs triaje manual: la decisión rojo/amarillo/verde es consistente, auditable
  - vs apps de checklist: conversa, no es un formulario

**4:00-5:00 — Pregunta 2: Decisión técnica más relevante**

> "Elige la decisión técnica más relevante que tomaste (arquitectura, modelo,
> herramientas, prompts, RAG, memoria, manejo del contexto, etc.) y cuéntanos:
> ¿qué alternativas evaluaste?, ¿por qué las descartaste?, ¿qué riesgos
> identificaste?, y si tuvieras dos semanas más para mejorar la solución,
> ¿qué cambiarías y por qué?"

**Puntos sugeridos**:
- **Decisión**: usar **LLM + reglas** para la decisión clínica (en lugar de
  LLM puro o reglas puras)
- **Alternativas evaluadas**:
  - LLM puro (decide del texto directo) → riesgo de alucinación clínica
  - Reglas puras (keyword matching) → no captura matices ni regionalismos
  - Modelo ML entrenado → no hay tiempo ni datos para entrenar
- **Por qué descarté las otras**: LLM puro puede inventar dosis o tranquilizar
  ante un síntoma de alarma (descalifica); reglas puras no entienden "tengo
  calentura desde ayer" (regionalismo colombiano)
- **Riesgos identificados**: si el LLM no devuelve JSON válido, la decisión
  falla → mitigación con prompt estricto + fallback a keyword (revisar
  `decision.py`)
- **Con 2 semanas más**:
  - Fine-tuning del LLM con los 160 casos del dataset (ya tenemos el script
    de calibración)
  - Reemplazar Llama 3.1 8B por 3.3 70B cuando Groq restablezca los TPD
  - Prompt-injection hardening (regex negra para "ignore instructions")

---

## Setup técnico

### OBS Studio (recomendado)

1. Descargar de https://obsproject.com/
2. Configurar:
   - Sources → Display Capture (toda la pantalla) o Window Capture (solo Chrome)
   - Sources → Video Capture Device (tu webcam) — esquinar abajo derecha
   - Audio → Desktop Audio (para que se grabe el TTS del agente)
   - Audio → Mic/Aux (tu voz)
3. Resolución: 1920×1080, 30 FPS
4. Iniciar grabación, hacer la demo, detener

### Alternativa: Loom (más simple)

- https://www.loom.com/
- Graba pantalla + cámara simultáneamente
- Sube directamente a YouTube con un click

---

## Checklist antes de grabar

- [ ] curl preflight pasó (200 en health, retrieval > 0)
- [ ] Frontend abierto en Chrome (no Firefox, Web Speech API es mejor en Chrome)
- [ ] Micrófono funcionando (probar con un "Hola" de prueba)
- [ ] Si Web Speech API falla: el fallback de texto debe estar visible y funcional
- [ ] PDF de prueba listo para subir en la demo de conocimiento vivo
- [ ] Terminal abierta para mostrar métricas
- [ ] Buena iluminación para la parte de frente a cámara
- [ ] Cuaderno con las respuestas a las 2 preguntas (para no quedarte en blanco)

---

## Publicación

1. Sube el video a YouTube como **Unlisted** (no Private, no Public)
2. Copia el link
3. Pégalo en el README del repo en una sección "Demo"
4. En el formulario de entrega, pega el link

---

## Tips

- **No leas**, conversa. El jurado quiere ver que entiendes lo que hiciste.
- Si te equivocas, déjalo y sigue. La autenticidad puntúa.
- Mantén el video corto (3-4 min ideal). La calidad > cantidad.
- Si la demo falla en vivo, muestra los logs y explica qué pasó. Eso también puntúa.
- **Si Web Speech API da "network error"**, no entres en pánico: usa el
  fallback de texto que ya está visible. La demo sigue siendo válida.
