"""Conversation flow and state management for the post-op voice agent.

Pure stdlib logic: deterministic topic progression, off-topic / hostile
detection, and instruction chunking. No LLM calls.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set


@dataclass
class ConversationState:
    paciente_id: str
    procedimiento: str
    dia_postoperatorio: int
    turns: List[Dict] = field(default_factory=list)
    summary_generated: bool = False


_TOPIC_KEYWORDS: Dict[str, tuple] = {
    "dolor": ("dolor", "molest", "duele", "duelen", "duela", "punza", "pulso"),
    "fiebre": ("fiebre", "temperatura", "calentur", "escalofr"),
    "herida": (
        "herida",
        "enrojeci",
        "enrojecido",
        "roja",
        "rojo",
        "secreci",
        "pus",
        "gasa",
        "punto",
        "cicatriz",
        "sutura",
    ),
    "apetito_sueno": (
        "apetit",
        "comi",
        "comer",
        "hambre",
        "sueñ",
        "dorm",
        "insomnio",
        "cansad",
    ),
    "movilidad": (
        "camin",
        "camine",
        "movil",
        "movimien",
        "levant",
        "parad",
        "cama",
    ),
    "alertas": (
        "sangr",
        "hemorrag",
        "respira",
        "ahog",
        "mareo",
        "desmay",
    ),
}

_TOPIC_ORDER: tuple = (
    "dolor",
    "fiebre",
    "herida",
    "apetito_sueno",
    "movilidad",
    "alertas",
)

_TOPIC_QUESTIONS: Dict[str, str] = {
    "dolor": "¿Qué nivel de dolor sientes ahora, en una escala de 0 a 10?",
    "fiebre": "¿Has tenido fiebre o temperatura alta en las últimas horas?",
    "herida": (
        "¿Cómo se ve tu herida quirúrgica? ¿Hay enrojecimiento, "
        "secreción o algún cambio?"
    ),
    "apetito_sueno": "¿Cómo van tu apetito y tu sueño desde la cirugía?",
    "movilidad": "¿Te has podido levantar y caminar un poco hoy?",
    "alertas": (
        "¿Has notado sangrado, dificultad para respirar o mareo intenso?"
    ),
}

_MEDICAL_KEYWORDS: tuple = (
    "dolor",
    "molest",
    "duele",
    "fiebre",
    "temperatura",
    "calentur",
    "escalofr",
    "herida",
    "enrojeci",
    "secreci",
    "pus",
    "gasa",
    "punto",
    "sangr",
    "hemorrag",
    "respira",
    "ahog",
    "mareo",
    "desmay",
    "nause",
    "vomit",
    "apetit",
    "hambre",
    "sueñ",
    "insomnio",
    "cansad",
    "camin",
    "movil",
    "levant",
    "cama",
    "medic",
    "pastill",
    "acetaminof",
    "ibuprofen",
    "antibiot",
    "curac",
    "curar",
    "vendaj",
)

_OFF_TOPIC_INTENT: tuple = (
    "cuesta",
    "costo",
    "precio",
    "pago",
    "factura",
    "seguro",
    "asegur",
    "quién eres",
    "quien eres",
    "que eres",
    "qué eres",
    "hola",
    "buenos dias",
    "buenas tardes",
    "buenos días",
)

_HOSTILE_KEYWORDS: tuple = (
    "porqueria",
    "porquería",
    "no sirve",
    "estupido",
    "estúpido",
    "inutil",
    "inútil",
    "tonto",
    "tonta",
    "basura",
    "horrible",
    "pesimo",
    "pésimo",
    "idiota",
    "imbecil",
    "imbécil",
    "maldito",
    "maldita",
    "odio",
    "asco",
    "patético",
    "patetico",
)

_SPLIT_RE = re.compile(r"[.;]\s*")
_COMMA_RE = re.compile(r",\s*")


def _topics_covered(turns: List[Dict]) -> Set[str]:
    covered: Set[str] = set()
    for turn in turns:
        content = (turn.get("content") or "").lower()
        if not content:
            continue
        for topic, keywords in _TOPIC_KEYWORDS.items():
            if topic in covered:
                continue
            if any(kw in content for kw in keywords):
                covered.add(topic)
    return covered


def next_question(state: ConversationState) -> str:
    covered = _topics_covered(state.turns)
    for topic in _TOPIC_ORDER:
        if topic not in covered:
            return _TOPIC_QUESTIONS[topic]
    if not state.summary_generated:
        return "¿Hay algo más que quieras reportar sobre tu recuperación?"
    return _TOPIC_QUESTIONS["dolor"]


def should_end_call(state: ConversationState) -> bool:
    return bool(state.summary_generated)


def handle_off_topic(text: str) -> str:
    normalized = (text or "").lower().strip()
    if not normalized:
        return ""

    if any(keyword in normalized for keyword in _HOSTILE_KEYWORDS):
        return (
            "Entiendo que estés pasando por un momento difícil y lamento "
            "mucho que te sientas así. Estoy aquí para acompañarte en tu "
            "recuperación postoperatoria. Cuéntame cómo te sientes y "
            "seguimos avanzando juntos, paso a paso."
        )

    if any(keyword in normalized for keyword in _OFF_TOPIC_INTENT):
        return (
            "Esa consulta queda fuera de mi alcance en este momento. Soy el "
            "asistente de seguimiento postoperatorio y solo puedo ayudarte "
            "con tu recuperación. Para temas administrativos, costos o "
            "trámites, por favor comunícate con la enfermería o consulta "
            "directamente al equipo médico del hospital."
        )

    if any(keyword in normalized for keyword in _MEDICAL_KEYWORDS):
        return ""

    return (
        "Esa consulta queda fuera de mi alcance en este momento. Soy el "
        "asistente de seguimiento postoperatorio y solo puedo ayudarte "
        "con tu recuperación. Para temas administrativos, costos o "
        "trámites, por favor comunícate con la enfermería o consulta "
        "directamente al equipo médico del hospital."
    )


def format_long_instructions(text: str) -> List[str]:
    if not text:
        return []
    raw_chunks = _SPLIT_RE.split(text)
    steps: List[str] = []
    for chunk in raw_chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        if len(chunk) > 90 and "," in chunk:
            parts = [p.strip() for p in _COMMA_RE.split(chunk) if p.strip()]
            steps.extend(parts)
        else:
            steps.append(chunk)
    return steps


class ConversationStore:
    """Adapter for api_app.py: stores turn-by-turn history per call_id."""
    def __init__(self):
        self._store: Dict[str, List[Dict]] = {}

    def append(self, call_id: str, transcript: str, response: str, decision: dict) -> None:
        self._store.setdefault(call_id, []).append({
            "transcript": transcript,
            "response": response,
            "decision": decision,
        })

    def history(self, call_id: str) -> List[Dict]:
        return self._store.get(call_id, [])
