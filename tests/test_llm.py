"""Tests for LLM client (Groq)."""
import pytest
from unittest.mock import MagicMock, patch
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


def test_generate_records_token_usage_on_last_usage():
    """generate() must stash the real Groq usage so callers can report
    tokens/cost — metrics.py has no other source for these numbers."""
    client = LLMClient(api_key="test_key")

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Hola, ¿cómo te sientes?"
    mock_response.usage.prompt_tokens = 123
    mock_response.usage.completion_tokens = 45
    mock_response.usage.total_tokens = 168

    with patch.object(
        client.client.chat.completions, "create", return_value=mock_response
    ):
        text = client.generate(transcript="hola")

    assert text == "Hola, ¿cómo te sientes?"
    assert client.last_usage == {
        "prompt_tokens": 123,
        "completion_tokens": 45,
        "total_tokens": 168,
    }

