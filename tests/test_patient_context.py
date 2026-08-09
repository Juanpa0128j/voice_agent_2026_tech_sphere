"""Tests for patient context loading and prompt injection."""
import pytest
from backend.patient_context import PatientContext, load_patient_context, build_context_prompt


def test_patient_context_creation():
    ctx = PatientContext(
        paciente_id="P001",
        nombre="Juan Pérez",
        procedimiento="Apendicectomía laparoscópica",
        dia_postoperatorio=3,
        comorbilidades=["Hipertensión"],
        eps="Sura",
    )
    assert ctx.paciente_id == "P001"
    assert ctx.nombre == "Juan Pérez"


def test_load_patient_context_from_dataset():
    ctx = load_patient_context("P001")
    assert ctx is not None
    assert ctx.paciente_id == "P001"
    assert ctx.nombre is not None
    assert ctx.procedimiento is not None


def test_load_patient_context_nonexistent():
    ctx = load_patient_context("NONEXISTENT")
    assert ctx is None


def test_build_context_prompt_includes_essential_info():
    ctx = PatientContext(
        paciente_id="P001",
        nombre="Juan Pérez",
        procedimiento="Apendicectomía",
        dia_postoperatorio=3,
        comorbilidades=[],
        eps="Sura",
    )
    prompt = build_context_prompt(ctx)
    assert "Juan Pérez" in prompt
    assert "Apendicectomía" in prompt
    assert "3" in prompt


def test_build_context_prompt_handles_empty_comorbilidades():
    ctx = PatientContext(
        paciente_id="P002",
        nombre="María López",
        procedimiento="Colecistectomía",
        dia_postoperatorio=1,
        comorbilidades=[],
        eps="Sanitas",
    )
    prompt = build_context_prompt(ctx)
    assert "Sin comorbilidades" in prompt or "ninguna" in prompt.lower()
