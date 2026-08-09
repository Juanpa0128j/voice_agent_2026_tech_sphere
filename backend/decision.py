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


class DecisionEngine:
    """Adapter class exposing the .decide() interface used by api_app.py.

    Decision flow:
      1. If Groq LLM available: extract structured symptoms via JSON, then apply
         clinical rules. This catches minimizer-style language ("tranquila
         doctora, un poquito molesto no más" + "37 y algo" + "rojita en el
         borde" = rojo).
      2. If LLM unavailable or fails: fall back to keyword scoring (faster but
         less accurate on conversational data).
    """

    def __init__(self, llm_client=None) -> None:
        self._llm = llm_client

    def decide(self, transcript: str, retrieval: List[Dict] = None, response: str = "") -> Dict[str, Any]:
        text = (transcript or "").strip()

        # Try LLM-based decision first
        if self._llm is None:
            try:
                from backend.llm import LLMClient
                self._llm = LLMClient()
            except Exception:
                self._llm = False  # sentinel: tried and failed, don't retry

        if self._llm and self._llm is not False:
            try:
                structured = self._extract_structured(self._llm, text)
                if structured:
                    return self._decide_from_structured(structured, source="llm")
            except Exception:
                pass  # fall through to keyword fallback

        # Keyword fallback
        result = decide_from_text(text)
        result["action"] = "respond"
        if result["label"] == "rojo":
            result["action"] = "alert"
        elif result["label"] == "amarillo":
            result["action"] = "warn"
        result["reason"] = result.get("rationale", "")
        result["source"] = "keyword"
        return result

    @staticmethod
    def _extract_structured(llm_client, text: str) -> Dict[str, Any]:
        """Ask LLM to extract structured symptoms as JSON. Returns dict or None."""
        import json, re
        messages = [
            {"role": "system", "content": STRUCTURED_DECISION_PROMPT},
            {"role": "user", "content": f"Transcripción del paciente:\n\n{text}\n\nDevuelve SOLO el JSON:"},
        ]
        result = llm_client._call(messages, temperature=0.0, max_tokens=300)
        content = result.get("content", "").strip()
        # Strip markdown code fences if present
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        try:
            return json.loads(content)
        except Exception:
            return None

    @staticmethod
    def _decide_from_structured(structured: Dict[str, Any], source: str = "llm") -> Dict[str, Any]:
        """Apply clinical rules to structured symptoms.

        Rules calibrated against the 160-case dataset:
          - rojo: any bleeding OR breathing difficulty, OR (fever >= 38.5 AND
            (wound infection signs OR pain >= 7)), OR (pain >= 8 alone with
            other symptoms), OR (fever >= 39 alone)
          - amarillo: fever 37.5-38.4, pain 5-7, wound erythema without pus,
            mild mobility reduction, persistent vomiting
          - verde: everything else
        """
        score = 0
        reasons: List[str] = []

        # Critical: any bleeding or breathing difficulty = rojo immediately
        if structured.get("sangrado"):
            score += 10
            reasons.append("sangrado activo")
        if structured.get("dificultad_respirar"):
            score += 10
            reasons.append("dificultad respiratoria")

        # Fever escalation
        fiebre = structured.get("fiebre_c")
        if fiebre is not None:
            if fiebre >= 39:
                score += 5
                reasons.append(f"fiebre {fiebre}°C (alta)")
            elif fiebre >= 38:
                score += 3
                reasons.append(f"fiebre {fiebre}°C (moderada)")
            elif fiebre >= 37.5:
                score += 1
                reasons.append(f"febrícula {fiebre}°C")

        # Pain escalation
        dolor = structured.get("dolor_eva")
        if dolor is not None and dolor >= 7:
            score += 3
            reasons.append(f"dolor EVA {dolor}/10")
        elif dolor is not None and dolor >= 5:
            score += 1
            reasons.append(f"dolor EVA {dolor}/10 (moderado)")

        # Wound infection
        if structured.get("secrecion"):
            score += 5
            reasons.append("secreción purulenta en herida")
        if structured.get("movilidad_limitada"):
            score += 2
            reasons.append("movilidad limitada")

        # Vomiting
        if structured.get("vomito"):
            score += 2
            reasons.append("vómito")

        # Combined rule: fever >= 38.5 + pain >= 7 = rojo
        if (fiebre is not None and fiebre >= 38.5 and
            dolor is not None and dolor >= 7):
            score = max(score, 8)
            reasons.append("combinación fiebre alta + dolor intenso")

        # Combined rule: fever >= 38.5 + wound secretion = rojo
        if (fiebre is not None and fiebre >= 38.5 and
            structured.get("secrecion")):
            score = max(score, 8)
            reasons.append("combinación fiebre alta + secreción")

        # Classify
        if score >= 6:
            label = "rojo"
        elif score >= 3:
            label = "amarillo"
        else:
            label = "verde"

        action = {"rojo": "alert", "amarillo": "warn", "verde": "respond"}[label]

        return {
            "label": label,
            "score": score,
            "rationale": "; ".join(reasons) if reasons else "sin síntomas relevantes",
            "alert": label in ("rojo", "amarillo"),
            "action": action,
            "reason": "; ".join(reasons) if reasons else "sin síntomas relevantes",
            "structured": structured,
            "source": source,
        }
