# Video Demo — Tech Sphere Challenge 2026

## Overview

- **Duración**: 3-5 minutos
- **Formato**: Screen recording + face cam para las 2 preguntas finales
- **Publicación**: YouTube unlisted (no aparece en búsquedas ni en tu canal)
- **Herramientas**: OBS Studio (gratis) o Loom

---

## Estructura del video

### Parte 1: Demo funcional (2-3 min)

**0:00-0:20 — Apertura**
- Mostrar el repo en GitHub: https://github.com/Juanpa0128j/voice_agent_2026_tech_sphere
- Señalar: LICENSE MIT, README, 53 tests pasando
- "Esto es un agente de voz con IA para seguimiento postoperatorio"

**0:20-0:50 — Stack y decisiones**
- Mencionar: Groq + Llama 3.3 70B, BGE-M3 + ChromaDB, Web Speech API
- "El stack es 100% open source, sin costo, corre en 8GB de RAM"

**0:50-1:30 — Demo de voz end-to-end**
- Abrir `http://localhost:8000/frontend/index.html` en Chrome
- Click en "Iniciar Llamada"
- Hablar (con tu voz o leer el guion abajo):
  1. "Hola"
  2. "Me operaron del apéndice hace 3 días"
  3. "Tengo dolor como 7 de 10"
  4. "Sí tengo fiebre, como 38.5"
  5. "La herida está un poco roja"
- El agente debe:
  - Responder con voz (TTS)
  - Mostrar el badge de decisión: primero verde, luego amarillo, finalmente **ROJO** (porque fiebre + herida roja + dolor alto)
  - Alertar al final

**1:30-2:00 — Conocimiento vivo**
- Abrir `frontend/admin.html` en otra pestaña
- Subir un PDF de prueba (puede ser cualquier PDF clínico)
- Mostrar que aparece en la lista con badge "Procesado y disponible"
- Volver a la pestaña de la llamada, hacer una pregunta que requiera ese documento
- Eliminar el documento, verificar que el agente ya no lo usa

**2:00-2:30 — Métricas**
- En terminal: `curl -s http://localhost:8000/api/metrics | python -m json.tool`
- Mostrar P50/P95, tokens, costo estimado
- Mencionar: ~$0.003 por llamada típica

---

### Parte 2: Preguntas frente a cámara (1-2 min)

**2:30-3:30 — Pregunta 1: Valor diferencial**

> "Si debes convencer a un cliente de que adopte el agente que construiste, ¿cómo presentarías el problema que resuelve, por qué tu solución es la adecuada y qué valor diferencial ofrece frente a otras alternativas?"

**Puntos sugeridos** (NO los leas, úsalos como guía mental):
- **Problema**: el seguimiento postoperatorio hoy depende de personal humano, es costoso, no escala, y está sujeto a errores
- **Por qué mi solución**: combina IA conversacional con RAG clínico, decisión automatizada con escalamiento, y conocimiento vivo (la consola permite actualizar las guías en caliente)
- **Valor diferencial vs alternativas**: a diferencia de un chatbot genérico, fundamenta cada respuesta en literatura médica citables; a diferencia de un call center humano, está disponible 24/7, escala infinitamente, y reduce costos operativos

**3:30-4:30 — Pregunta 2: Decisión técnica más relevante**

> "Elige la decisión técnica más relevante que tomaste y cuéntanos: ¿qué alternativas evaluaste?, ¿por qué las descartaste?, ¿qué riesgos identificaste?, y si tuvieras dos semanas más para mejorar la solución, ¿qué cambiarías y por qué?"

**Puntos sugeridos**:
- **Decisión**: usar LLM + reglas para la decisión clínica (en lugar de LLM puro o reglas puras)
- **Alternativas evaluadas**:
  - LLM puro (decide del texto directo) → riesgo de alucinación
  - Reglas puras (keyword matching) → no captura matices del lenguaje natural
  - Modelo ML entrenado → no hay tiempo ni datos
- **Por qué descarté las otras**: LLM puro puede alucinar ("el agente dice que tomes acetaminofén cada 4 horas cuando debe ser cada 8"); reglas puras no entienden "tengo calentura desde ayer" (regionalismo)
- **Riesgos identificados**: si el LLM no devuelve JSON válido, la decisión falla → mitigación con prompt estricto + fallback a keyword
- **Con 2 semanas más**: fine-tuning del LLM con los 160 casos del dataset

---

## Setup técnico

### OBS Studio (recomendado)

1. Descargar de https://obsproject.com/
2. Configurar:
   - Sources → Display Capture (toda la pantalla) o Window Capture (solo Chrome)
   - Sources → Video Capture Device (tu webcam)
   - Audio → Desktop Audio (para que se grabe el TTS del agente)
   - Audio → Mic/Aux (tu voz)
3. Resolución: 1920x1080, 30 FPS
4. Iniciar grabación, hacer la demo, detener

### Alternativa: Loom (más simple)

- https://www.loom.com/
- Graba pantalla + cámara simultáneamente
- Sube directamente a YouTube con un click

---

## Checklist antes de grabar

- [ ] `docker compose up` corriendo
- [ ] Frontend abierto en Chrome (no Firefox, Web Speech API es mejor en Chrome)
- [ ] Micrófono funcionando (probar con un "Hola" de prueba)
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
