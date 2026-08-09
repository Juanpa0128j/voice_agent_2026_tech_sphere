"""Structured call summary generation and persistence."""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


SUMMARY_SCHEMA: Dict[str, str] = {
    "call_id": "string (UUID)",
    "paciente_id": "string",
    "nombre": "string",
    "procedimiento": "string",
    "dia_postoperatorio": "integer",
    "sintomas_reportados": "array of strings",
    "decision": "string (verde|amarillo|rojo)",
    "fuentes": "array of {id, excerpt}",
    "proximos_pasos": "array of strings",
    "alerta_enviada": "boolean",
    "timestamp": "ISO 8601 string",
}


_SINTOMA_KEYWORDS: Dict[str, str] = {
    "dolor": "dolor",
    "fiebre": "fiebre",
    "sangrado": "sangrado",
    "infeccion": "infeccion",
    "infecc": "infeccion",
    "nausea": "nausea",
    "vomit": "vomito",
    "inflam": "inflamacion",
    "edema": "edema",
    "enrojeci": "enrojecimiento",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_value(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(0).strip()


def _extract_symptom(text: str) -> str | None:
    lowered = text.lower()
    for keyword, label in _SINTOMA_KEYWORDS.items():
        if keyword in lowered:
            scale = _extract_value(text, r"\d+(?:[.,]\d+)?\s*/\s*10|\d+(?:[.,]\d+)?\s*grados|\d+(?:[.,]\d+)?\s*°\s*c?")
            if scale:
                return f"{label} {scale}"
            return label
    return None


def _extract_symptoms(turns: List[Dict[str, Any]]) -> List[str]:
    sintomas: List[str] = []
    for turn in turns:
        if turn.get("role") != "user":
            continue
        content = str(turn.get("content", ""))
        for sentence in re.split(r"[.;\n]", content):
            symptom = _extract_symptom(sentence)
            if symptom and symptom not in sintomas:
                sintomas.append(symptom)
    return sintomas


def _next_steps_for(decision: str, dia_postoperatorio: int) -> List[str]:
    if decision == "verde":
        return [
            "Reposo relativo",
            "Continuar medicación",
            f"Control en {dia_postoperatorio + 7} días",
        ]
    if decision == "amarillo":
        return [
            "Contactar a su médico en las próximas horas",
            "Vigilar síntomas",
        ]
    if decision == "rojo":
        return [
            "Acudir a urgencias inmediatamente",
            "No automedicar",
        ]
    return []


@dataclass
class CallSummary:
    call_id: str
    paciente_id: str
    nombre: str
    procedimiento: str
    dia_postoperatorio: int
    sintomas_reportados: List[str]
    decision: str
    fuentes: List[Dict[str, Any]]
    proximos_pasos: List[str]
    alerta_enviada: bool
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def generate_summary(
    paciente_id: str,
    nombre: str,
    procedimiento: str,
    dia_postoperatorio: int,
    turns: List[Dict[str, Any]],
    decision: Dict[str, Any],
    sources: List[Dict[str, Any]],
) -> Dict[str, Any]:
    decision_label = str(decision.get("label", "verde"))
    alerta = bool(decision.get("alert", False))

    sintomas = _extract_symptoms(turns)
    proximos_pasos = _next_steps_for(decision_label, dia_postoperatorio)

    summary: Dict[str, Any] = {
        "call_id": str(uuid.uuid4()),
        "paciente_id": paciente_id,
        "nombre": nombre,
        "procedimiento": procedimiento,
        "dia_postoperatorio": dia_postoperatorio,
        "sintomas_reportados": sintomas,
        "decision": decision_label,
        "fuentes": list(sources),
        "proximos_pasos": proximos_pasos,
        "alerta_enviada": alerta,
        "timestamp": _now_iso(),
    }
    return summary


def save_summary(summary: CallSummary, dir_path: str) -> Path:
    directory = Path(dir_path)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{summary.call_id}.json"
    path.write_text(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_summary(path: Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


class SummaryService:
    """Adapter for api_app.py: generates + persists call summaries."""
    def __init__(self, calls_dir: str = "backend/calls"):
        from pathlib import Path
        self.calls_dir = Path(calls_dir)
        self.calls_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Dict] = {}

    def summarize(self, call_id: str) -> Dict[str, Any]:
        if call_id in self._cache:
            return self._cache[call_id]
        for path in self.calls_dir.glob(f"{call_id}.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            self._cache[call_id] = data
            return data
        raise KeyError(call_id)

    def save(self, summary_dict: Dict[str, Any]) -> str:
        call_id = summary_dict.get("call_id") or uuid.uuid4().hex
        summary_dict["call_id"] = call_id
        path = self.calls_dir / f"{call_id}.json"
        path.write_text(json.dumps(summary_dict, ensure_ascii=False, indent=2), encoding="utf-8")
        self._cache[call_id] = summary_dict
        return call_id
