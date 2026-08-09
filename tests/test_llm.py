"""Tests for LLM client (Groq)."""
import pytest
from backend.llm import LLMClient, build_messages


def test_llm_client_initialization():
    client = LLMClient(api_key="test_key", model="llama-3.3-70b-versatile")
    assert client.model == "llama-3.3-70b-versatile"
    assert client.api_key == "test_key"


def test_build_messages_simple():
    messages = build_messages(
        system_prompt="Eres un médico.",
        conversation=[{"role": "user", "content": "Hola"}],
    )
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_build_messages_with_context():
    messages = build_messages(
        system_prompt="Eres un médico.",
        conversation=[{"role": "user", "content": "Tengo fiebre"}],
        context_docs=["Doc 1: fiebre postoperatoria", "Doc 2: cuidado de herida"],
    )
    system_content = messages[0]["content"]
    assert "Doc 1" in system_content
    assert "Doc 2" in system_content

