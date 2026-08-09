"""Tests for call summary generation and persistence."""
import pytest
import json
from pathlib import Path
from backend.summary import (
    CallSummary,
    generate_summary,
    save_summary,
    load_summary,
    SUMMARY_SCHEMA,
)


def test_call_summary_creation():
    s = CallSummary(
        call_id="c001",
        paciente_id="P001",
        nombre="Juan",
        procedimiento="Apendicectomía",
        dia_postoperatorio=3,
        sintomas_reportados=["dolor 7/10", "fiebre 38.5"],
        decision="amarillo",
        fuentes=[],
        proximos_pasos=["Tomar acetaminofén"],
        alerta_enviada=True,
    )
    assert s.call_id == "c001"
    assert s.decision == "amarillo"


def test_generate_summary_from_conversation():
    turns = [
        {"role": "user", "content": "Tengo dolor 7 de 10"},
        {"role": "assistant", "content": "¿Tiene fiebre?"},
        {"role": "user", "content": "Sí, 38.5 grados"},
    ]
    decision = {"label": "amarillo", "alert": True}
    sources = [{"id": "d1", "excerpt": "fiebre postoperatoria"}]
    summary = generate_summary(
        paciente_id="P001",
        nombre="Juan",
        procedimiento="Apendicectomía",
        dia_postoperatorio=3,
        turns=turns,
        decision=decision,
        sources=sources,
    )
    assert "dolor" in str(summary["sintomas_reportados"]).lower()
    assert summary["decision"] == "amarillo"


def test_save_and_load_summary(tmp_path):
    s = CallSummary(
        call_id="c002",
        paciente_id="P002",
        nombre="María",
        procedimiento="Colecistectomía",
        dia_postoperatorio=1,
        sintomas_reportados=["dolor leve"],
        decision="verde",
        fuentes=[],
        proximos_pasos=["Reposo"],
        alerta_enviada=False,
    )
    path = tmp_path / "calls"
    path.mkdir()
    save_summary(s, str(path))
    files = list(path.glob("*.json"))
    assert len(files) == 1
    loaded = load_summary(files[0])
    assert loaded["paciente_id"] == "P002"


def test_summary_schema_has_required_fields():
    required = ["call_id", "paciente_id", "procedimiento", "decision", "sintomas_reportados"]
    for field in required:
        assert field in SUMMARY_SCHEMA


def test_summary_serializes_to_json():
    s = CallSummary(
        call_id="c003",
        paciente_id="P003",
        nombre="Pedro",
        procedimiento="Reemplazo de rodilla",
        dia_postoperatorio=7,
        sintomas_reportados=[],
        decision="verde",
        fuentes=[],
        proximos_pasos=[],
        alerta_enviada=False,
    )
    data = s.to_dict()
    json_str = json.dumps(data)
    parsed = json.loads(json_str)
    assert parsed["call_id"] == "c003"
