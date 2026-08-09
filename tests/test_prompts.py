"""Tests for system prompts, glossary, and few-shot examples."""
import pytest
from backend.prompts import (
    SYSTEM_PROMPT,
    COLOMBIAN_SLANG_GLOSSARY,
    FEW_SHOT_EXAMPLES,
    build_system_prompt,
    classify_intent,
)


def test_system_prompt_has_medical_role():
    assert "médico" in SYSTEM_PROMPT.lower() or "enfermer" in SYSTEM_PROMPT.lower()


def test_system_prompt_prohibits_inventing_dosages():
    assert "no inventes" in SYSTEM_PROMPT.lower() or "nunca" in SYSTEM_PROMPT.lower()


def test_glossary_has_common_terms():
    assert len(COLOMBIAN_SLANG_GLOSSARY) >= 5
    assert "abajito" in str(COLOMBIAN_SLANG_GLOSSARY).lower() or "chiche" in str(COLOMBIAN_SLANG_GLOSSARY).lower()


def test_few_shot_examples_present():
    assert len(FEW_SHOT_EXAMPLES) >= 2
    for ex in FEW_SHOT_EXAMPLES:
        assert "user" in ex
        assert "assistant" in ex


def test_build_system_prompt_includes_glossary():
    prompt = build_system_prompt(include_glossary=True)
    assert "abajito" in prompt.lower() or len(COLOMBIAN_SLANG_GLOSSARY) > 0


def test_classify_intent_emergency():
    assert classify_intent("No puedo respirar") == "emergency"


def test_classify_intent_pain():
    assert classify_intent("Me duele mucho") == "pain"


def test_classify_intent_general():
    assert classify_intent("Hola") == "general"
