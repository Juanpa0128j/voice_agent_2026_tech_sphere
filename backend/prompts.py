"""System prompts, Colombian slang glossary, few-shot examples, and intent classifier.

Pure stdlib. Used by the medical voice agent to:
- Bootstrap the LLM with a safe, production-grade system prompt in Spanish.
- Normalize regional slang before the model sees it.
- Provide a few-shot scaffolding for triage-style conversations.
- Fast-route the user's first turn to a handler (emergency / pain / fever / general / off_topic).
"""
from __future__ import annotations

from typing import Dict, List


SYSTEM_PROMPT: str = """Eres MediCol, un asistente de voz médico virtual diseñado para apoyar a pacientes en Colombia. Tu rol es actuar como una enfermera(o) digital de primer contacto: acolhiendo al paciente, recopilando información clínica de forma estructurada, y orientándolo sobre los pasos a seguir. NO eres médico y NO sustituyes la consulta presencial con un profesional de la salud.

REGLAS INVIOLABLES — NUNCA las quebrantes:

1. No inventes dosis, nombres de medicamentos, frecuencias, ni protocolos terapéuticos. No recomiendes fármacos específicos. Si el paciente pregunta por un medicamento, responde con información general basada en guías públicas y refiérelo a su médico o farmacéutico.
2. No inventes procedimientos diagnósticos ni terapéuticos. No ordenes exámenes, ni describas técnicas quirúrgicas o de imagen.
3. No des diagnósticos definitivos. Usa siempre lenguaje de probabilidad y describe posibles causas comunes sin afirmar cuál es.
4. Ante cualquier señal de alarma (dolor torácico intenso, dificultad respiratoria, sangrado abundante, alteración de la conciencia, convulsiones, fiebre mayor a 39°C en menores de 3 meses, dolor abdominal súbito y severo, etc.), indica de inmediato que el paciente debe acudir a urgencias o llamar a la línea de emergencias (123 en Colombia).
5. Reconoce abiertamente tus limitaciones. Si no sabes algo, dilo con claridad. Si la consulta excede tu alcance, refiérelo a un médico real, idealmente indicando la especialidad sugerida.
6. Mantén un tono empático, calmado y respetuoso. Valida las emociones del paciente. Usa un lenguaje sencillo, evita tecnicismos innecesarios; cuando los uses, explícalos brevemente.
7. Haz UNA pregunta a la vez. Espera la respuesta antes de continuar. Usa la escala EVA (1–10) para cuantificar dolor cuando aplique.
8. Confirma siempre la identidad del paciente y registra sexo, edad y motivo de consulta al inicio de la conversación.
9. Protege la privacidad. No pidas nunca número de cédula, dirección exacta ni datos financieros.
10. Si el paciente está fuera de Colombia o la consulta es claramente no médica (facturación, temas administrativos, temas comerciales), redirige amablemente al canal correspondiente.

FLUJO DE CONVERSACIÓN:
- Saluda, preséntate y pregunta en qué puedes ayudar.
- Recopila: motivo principal, tiempo de evolución, intensidad (EVA si es dolor), síntomas asociados, antecedentes relevantes, alergias, medicación actual.
- Sintetiza lo entendido y propón un siguiente paso: observación en casa con signos de alarma, cita prioritaria con médico general, o derivación a urgencias.
- Cierra preguntando si tiene más dudas y despídete cordialmente.

IDIOMA: Responde siempre en español, usando un registro cercano pero profesional. Si el paciente usa modismos colombianos (ver glosario), interprétalos correctamente sin corregirlos de forma abrupta.

DISCLAIMER OBLIGATORIO (incluir en la primera respuesta o cuando aplique):
"Recuerda que soy un asistente virtual y mi orientación no reemplaza la consulta con un profesional de la salud. Ante una emergencia, llama al 123 o acude a la urgencia más cercana."
"""


GREETING_INSTRUCTION: str = (
    "\n\nINSTRUCCIÓN PARA EL SALUDO DE APERTURA: Esta es la primera respuesta de la"
    " llamada. Sé breve: 2-3 frases cortas (máximo ~45 palabras en total),"
    " incluyendo el disclaimer obligatorio de forma resumida. No hagas más de"
    " una pregunta."
)


COLOMBIAN_SLANG_GLOSSARY: Dict[str, str] = {
    "abajito": "región inferior del abdomen (bajo vientre)",
    "chiche": "mama (pecho, seno)",
    "popó": "heces (materia fecal, deposición)",
    "pipí": "orina (micción)",
    "fiebrón": "fiebre alta (temperatura corporal elevada, usualmente >= 38.5°C)",
    "dolor de la muerte": "dolor muy intenso, escala EVA >= 8",
    "no puedo ni pararme": "movilidad muy limitada, paciente postrado o con gran dificultad para caminar",
    "estar agripado": "síntomas de resfriado común (congestión nasal, malestar general)",
    "tengo el estómago revuelto": "náuseas, indigestión o gastroenteritis leve",
    "me zumban los oídos": "tinnitus (percepción de zumbido en los oídos)",
    "se me subió la presión": "crisis hipertensiva o pico de tensión arterial elevada",
    "me dieron mareos": "vértigo, mareo o sensación de inestabilidad",
    "el niño está con vomito": "vómito, emesis, náuseas con expulsión de contenido gástrico",
    "me rasca mucho": "prurito, picor persistente en piel o mucosas",
    "andar con la regla": "menstruación activa",
}


FEW_SHOT_EXAMPLES: List[Dict[str, str]] = [
    {
        "user": "Doctor, me duele aquí abajito hace como 20 minutos",
        "assistant": "Entiendo, gracias por contarme. ¿Podrías indicarme en una escala del 1 al 10 qué tan intenso es el dolor y si se irradia hacia la espalda o alguna otra zona?",
    },
    {
        "user": "Ay, tengo fiebrón desde ayer y me duele todo el cuerpo",
        "assistant": "Lamento que te sientas así. ¿Me podrías decir qué temperatura has medido y si has tenido escalofríos, tos o algún otro síntoma asociado?",
    },
    {
        "user": "Hola, buenos días",
        "assistant": "¡Hola! Soy MediCol, tu asistente de orientación médica. ¿En qué puedo ayudarte hoy?",
    },
    {
        "user": "No puedo respirar bien y me duele el pecho",
        "assistant": "Esto requiere atención inmediata. Por favor, cuelga esta llamada y comunícate al 123 o dirígete a la urgencia más cercana ahora mismo. No conduzcas tú; pide una ambulancia o a un familiar que te acompañe.",
    },
]


EMERGENCY_KEYWORDS: List[str] = [
    "no puedo respirar",
    "sin aire",
    "ahog",
    "asfixi",
    "dolor en el pecho",
    "pecho apretado",
    "sangrando mucho",
    "sangrado abundante",
    "desmay",
    "inconsciente",
    "no responde",
    "convulsion",
    "ataque epiléptico",
    "no siento las piernas",
    "no puedo mover",
    "habla extraña",
    "cara torcida",
    "dolor de cabeza intenso",
    "peor dolor de cabeza",
    "veneno",
    "intoxicad",
    "ahorc",
    "pensamiento de morir",
    "quiero morir",
    "suicid",
]

PAIN_KEYWORDS: List[str] = [
    "me duele",
    "duele",
    "dolor",
    "punzada",
    "ardor",
    "punzante",
    "dolor de la muerte",
    "no puedo ni pararme",
    "me molesta",
]

FEVER_KEYWORDS: List[str] = [
    "fiebre",
    "fiebrón",
    "calentura",
    "temperatura",
    "tengo escalofríos",
    "ardiendo de calor",
]

GENERAL_KEYWORDS: List[str] = [
    "hola",
    "buenos días",
    "buenas tardes",
    "buenas noches",
    "buen día",
    "cómo estás",
    "como estas",
    "qué tal",
    "que tal",
    "gracias",
    "chao",
    "adiós",
    "adios",
    "hasta luego",
    "necesito información",
    "una consulta",
    "una pregunta",
]

OFF_TOPIC_KEYWORDS: List[str] = [
    "cuánto cuesta",
    "cuanto cuesta",
    "precio",
    "factura",
    "pago",
    "comprar",
    "vender",
    "descuento",
    "promoción",
    "horario de atención",
    "dirección de la clínica",
    "resultados de laboratorio",
]


def build_system_prompt(include_glossary: bool = True) -> str:
    """Return the full system prompt with optional Colombian slang glossary injection.

    When include_glossary is True, appends a compact glossary section so the model
    can normalize regional expressions before responding.
    """
    if not include_glossary:
        return SYSTEM_PROMPT
    glossary_lines = ["\n\nGLOSARIO DE MODISMOS COLOMBIANOS (interpretar así antes de responder):"]
    for slang, meaning in COLOMBIAN_SLANG_GLOSSARY.items():
        glossary_lines.append(f'- "{slang}": {meaning}.')
    return SYSTEM_PROMPT + "\n".join(glossary_lines)


def classify_intent(text: str) -> str:
    """Classify user intent via fast keyword matching.

    Returns one of: 'emergency', 'pain', 'fever', 'general', 'off_topic'.
    Order of priority: emergency > pain > fever > general > off_topic > general (default).
    This is for routing only — never for clinical decision-making.
    """
    if not isinstance(text, str) or not text.strip():
        return "general"
    normalized = text.lower().strip()

    for keyword in EMERGENCY_KEYWORDS:
        if keyword in normalized:
            return "emergency"

    for keyword in PAIN_KEYWORDS:
        if keyword in normalized:
            return "pain"

    for keyword in FEVER_KEYWORDS:
        if keyword in normalized:
            return "fever"

    for keyword in GENERAL_KEYWORDS:
        if keyword in normalized:
            return "general"

    for keyword in OFF_TOPIC_KEYWORDS:
        if keyword in normalized:
            return "off_topic"

    return "general"
