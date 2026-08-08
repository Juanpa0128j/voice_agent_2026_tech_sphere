"""Decision logic and simple alerting rules for post-op agent.
This module exposes a rule-based classifier that consumes a structured call summary
and returns a severity label (verde/amarillo/rojo) and a short rationale.

It also provides a simple provenance wrapper to attach source document ids.
"""
from typing import Dict, Any, List, Tuple

# simple keywords mapping to severity points
KEYWORD_SCORES = {
    'fiebre': 3,
    'fiebre alta': 4,
    'sangrado': 5,
    'hemorragia': 5,
    'dolor intenso': 3,
    'dolor': 1,
    'no puede respirar': 5,
    'dificultad para respirar': 5,
    'enrojecimiento': 2,
    'secreción purulenta': 4,
    'rojo': 4,
}

THRESHOLDS = {
    'rojo': 6,
    'amarillo': 3,
    'verde': 0,
}


def score_from_text(text: str) -> int:
    t = text.lower()
    score = 0
    for k,v in KEYWORD_SCORES.items():
        if k in t:
            score += v
    return score


def decide(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Return decision dict: {label, score, rationale, alert (bool)}
    summary expected keys: 'transcript' (str), optional 'structured' dict
    """
    text = summary.get('transcript','')
    if not text and 'structured' in summary:
        # build text from structured
        parts = []
        for k,v in summary.get('structured', {}).items():
            parts.append(f"{k}: {v}")
        text = ' '.join(parts)

    score = score_from_text(text)
    label = 'verde'
    if score >= THRESHOLDS['rojo']:
        label = 'rojo'
    elif score >= THRESHOLDS['amarillo']:
        label = 'amarillo'

    rationale = f"score={score}; matched keywords from transcript"
    alert = label in ('amarillo','rojo')
    return {
        'label': label,
        'score': score,
        'rationale': rationale,
        'alert': alert,
    }


# provenance helper

def attach_provenance(response: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Wrap a textual response with provenance metadata.
    sources: list of {id: str, path: str, excerpt: str}
    """
    return {
        'response': response,
        'provenance': sources,
    }
