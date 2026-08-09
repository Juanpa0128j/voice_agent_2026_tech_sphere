"""Tests for conversation flow and state management."""
import pytest
from backend.conversation import (
    ConversationState,
    next_question,
    should_end_call,
    format_long_instructions,
    handle_off_topic,
)


def test_conversation_state_creation():
    state = ConversationState(
        paciente_id="P001",
        procedimiento="Apendicectomía",
        dia_postoperatorio=3,
    )
    assert state.paciente_id == "P001"
    assert state.turns == []


def test_next_question_asks_about_pain_first():
    state = ConversationState("P001", "Apendicectomía", 3)
    q = next_question(state)
    assert "dolor" in q.lower() or "molest" in q.lower()


def test_next_question_progresses_through_topics():
    state = ConversationState("P001", "Apendicectomía", 3)
    state.turns.append({"role": "user", "content": "Tengo dolor 7 de 10"})
    q = next_question(state)
    assert "fiebre" in q.lower() or "temperatura" in q.lower() or "herida" in q.lower()


def test_should_end_call_after_summary():
    state = ConversationState("P001", "Apendicectomía", 3)
    state.summary_generated = True
    assert should_end_call(state) is True


def test_format_long_instructions_splits_into_steps():
    text = "Toma acetaminofén 500mg cada 8 horas por 7 días. Lava la herida con agua y jabón. Cambia la gasa cada 12 horas. Acude a urgencias si sangras mucho."
    steps = format_long_instructions(text)
    assert len(steps) >= 3


def test_handle_off_topic_redirects():
    response = handle_off_topic("¿Cuánto cuesta la cirugía?")
    assert "enfermer" in response.lower() or "médic" in response.lower() or "consult" in response.lower()


def test_handle_hostile_patient_calms():
    response = handle_off_topic("Esto es una porquería, no sirve para nada")
    assert len(response) > 10
