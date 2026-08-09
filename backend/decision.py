"""Decision logic and alerting rules for post-op agent.

Rule-based severity classifier (verde / amarillo / rojo) that consumes either
raw transcript text or a structured symptom dict and returns a decision with
label, score, rationale, and alert flag.

Pure deterministic logic — no external API calls.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


STRUCTURED_DECISION_PROMPT: str = (
    "Eres un asistente clínico que extrae síntomas estructurados desde la "
    "transcripción de una llamada postoperatoria de seguimiento.\n\n"
    "Devuelve EXCLUSIVAMENTE un objeto JSON válido (sin texto adicional, sin "
    "bloques de código markdown) con esta forma exacta:\n"
    "{\n"
    '  "dolor_eva": <entero 0-10, o null si no se menciona>,\n'
    '  "fiebre_c": <número en grados Celsius, o null si no se menciona>,\n'
    '  "secrecion": <true si hay secreción purulenta o mal olor en la herida>,\n'
    '  "sangrado": <true si hay sangrado activo o hemorragia>,\n'
    '  "dificultad_respirar": <true si hay disnea, ahogo o no puede respirar>,\n'
    '  "vomito": <true si hay vómito persistente>,\n'
    '  "movilidad_limitada": <true si la movilidad está más limitada de lo '
    "esperado para el día postoperatorio>\n"
    "}\n\n"
    "Reglas:\n"
    "- Si el síntoma no se menciona, usa null para números y false para booleanos.\n"
    "- No inventes valores. Si el paciente dice 'no tengo fiebre', entonces "
    "fiebre_c = null.\n"
    "- dolor_eva es la escala verbal numérica de 0 (sin dolor) a 10 (peor dolor "
    "imaginable).\n"
    "- Si el paciente describe el dolor con palabras ('mucho dolor', 'dolor "
    "fuerte'), estima el EVA correspondiente."
)


# Keyword rules: (substring, points). Substring match is case-insensitive.
# Multiple patterns can match the same text (e.g. "fiebre alta" also matches
# "fiebre") — additive scoring is intentional and slightly conservative.
KEYWORD_PATTERNS: List[Tuple[str, int]] = [
    # Critical: bleeding (5)
    ("sangrado", 5),
    ("sangrando", 5),
    ("sangre", 5),
    ("hemorragia", 5),
    # Intensifier (1) — adds signal to active-bleeding phrases
    ("mucho", 1),
    # Critical: breathing (5)
    ("dificultad para respirar", 5),
    ("no puedo respirar", 5),
    ("no puede respirar", 5),
    ("ahogo", 5),
    ("ahogando", 5),
    ("asfixia", 5),
    # Distress marker (1) — adds signal to critical phrases like "no puedo..."
    ("no puedo", 1),
    # High fever (4)
    ("fiebre alta", 4),
    ("fiebrón", 4),
    ("calentura", 4),
    ("39 grados", 4),
    ("40 grados", 4),
    ("39°", 4),
    ("40°", 4),
    # Wound infection signs (4)
    ("secreción purulenta", 4),
    ("mal olor", 4),
    ("pus", 4),
    # Urinary retention (4)
    ("no puedo orinar", 4),
    ("no puede orinar", 4),
    ("no puedo hacer pipí", 4),
    # Severe pain (3)
    ("dolor intenso", 3),
    ("dolor fuerte", 3),
    ("10 de 10", 3),
    ("9 de 10", 3),
    ("8 de 10", 3),
    # General fever (3)
    ("fiebre", 3),
    ("temperatura", 3),
    # Neuro (3)
    ("mareo", 3),
    ("desmayo", 3),
    # Vomiting (2)
    ("vómito", 2),
    ("vomito", 2),
    ("vomitando", 2),
    # Local inflammation (2)
    ("enrojecimiento", 2),
    ("caliente", 2),
    # Color flag (2)
    ("rojo", 2),
    # General pain (1)
    ("dolor", 1),
]


THRESHOLDS: Dict[str, int] = {
    "rojo": 6,
    "amarillo": 3,
    "verde": 0,
}


def score_from_text(text: str) -> int:
    """Score symptom severity from raw text using keyword matching.

    Returns 0 for empty, None, or non-string input.
    """
    if not text or not isinstance(text, str):
        return 0
    t = text.lower()
    score = 0
    for pattern, points in KEYWORD_PATTERNS:
        if pattern in t:
            score += points
    return score


def severity_from_score(score: int) -> str:
    """Map an integer score to a severity label.

    Thresholds:
        score >= 6 -> "rojo"
        score >= 3 -> "amarillo"
        else       -> "verde"
    """
    try:
        s = int(score)
    except (TypeError, ValueError):
        return "verde"
    if s >= THRESHOLDS["rojo"]:
        return "rojo"
    if s >= THRESHOLDS["amarillo"]:
        return "amarillo"
    return "verde"


def _score_from_structured(structured: Dict[str, Any]) -> int:
    """Score a structured symptom dict (LLM-extracted).

    Keys: dolor_eva (0-10), fiebre_c (Celsius), secrecion, sangrado,
    dificultad_respirar, vomito, movilidad_limitada (bools).
    """
    if not isinstance(structured, dict):
        return 0
    score = 0

    dolor = structured.get("dolor_eva")
    if isinstance(dolor, (int, float)) and not isinstance(dolor, bool):
        if dolor >= 8:
            score += 3
        elif dolor >= 4:
            score += 1

    fiebre = structured.get("fiebre_c")
    if isinstance(fiebre, (int, float)) and not isinstance(fiebre, bool):
        if fiebre >= 39:
            score += 4
        elif fiebre >= 38:
            score += 3
        elif fiebre >= 37.5:
            score += 1

    if structured.get("sangrado"):
        score += 5
    if structured.get("dificultad_respirar"):
        score += 5
    if structured.get("secrecion"):
        score += 4
    if structured.get("vomito"):
        score += 2
    if structured.get("movilidad_limitada"):
        score += 1

    return score


def _rationale_from_structured(structured: Dict[str, Any]) -> str:
    parts: List[str] = []
    dolor = structured.get("dolor_eva")
    if isinstance(dolor, (int, float)) and not isinstance(dolor, bool):
        parts.append(f"EVA={dolor}")
    fiebre = structured.get("fiebre_c")
    if isinstance(fiebre, (int, float)) and not isinstance(fiebre, bool):
        parts.append(f"T={fiebre}C")
    for key in ("sangrado", "dificultad_respirar", "secrecion", "vomito", "movilidad_limitada"):
        if structured.get(key):
            parts.append(key.replace("_", " "))
    return "; ".join(parts) if parts else "sin hallazgos"


def decide_from_text(text: str) -> Dict[str, Any]:
    """Decide severity from raw transcript text.

    Returns: {label, score, rationale, alert (bool)}
    """
    score = score_from_text(text)
    label = severity_from_score(score)
    return {
        "label": label,
        "score": score,
        "rationale": f"score={score} (keyword)",
        "alert": label in ("amarillo", "rojo"),
    }


def decide(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Decide severity from a summary dict.

    `summary` may contain:
        - 'transcript' (str): raw call text -> keyword scoring
        - 'structured' (dict): extracted symptoms -> field-based scoring
        If both, 'structured' takes precedence.

    Returns: {label, score, rationale, alert (bool)}
    """
    if not isinstance(summary, dict):
        return {"label": "verde", "score": 0, "rationale": "summary inválido", "alert": False}

    structured = summary.get("structured")
    if isinstance(structured, dict) and structured:
        score = _score_from_structured(structured)
        label = severity_from_score(score)
        return {
            "label": label,
            "score": score,
            "rationale": _rationale_from_structured(structured),
            "alert": label in ("amarillo", "rojo"),
        }

    text = summary.get("transcript", "") or ""
    return decide_from_text(text)


def attach_provenance(response: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Wrap a textual response with provenance metadata.

    sources: list of {id: str, path: str, excerpt: str}
    """
    return {
        "response": response,
        "provenance": sources,
    }


class DecisionEngine:
    """Adapter class exposing the .decide() interface used by api_app.py."""

    def decide(self, transcript: str, retrieval: List[Dict] = None, response: str = "") -> Dict[str, Any]:
        text = transcript or ""
        result = decide_from_text(text)
        result["action"] = "respond"
        if result["label"] == "rojo":
            result["action"] = "alert"
        elif result["label"] == "amarillo":
            result["action"] = "warn"
        result["reason"] = result.get("rationale", "")
        return result
