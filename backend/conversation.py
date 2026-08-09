"""Conversation flow and state management for the post-op voice agent.

Pure stdlib logic: turn-by-turn call history storage. No LLM calls.
"""
from __future__ import annotations

from typing import Dict, List


class ConversationStore:
    """Adapter for api_app.py: stores turn-by-turn history per call_id."""
    def __init__(self):
        self._store: Dict[str, List[Dict]] = {}

    def append(self, call_id: str, transcript: str, response: str, decision: dict) -> None:
        self._store.setdefault(call_id, []).append({
            "transcript": transcript,
            "response": response,
            "decision": decision,
        })

    def history(self, call_id: str) -> List[Dict]:
        return self._store.get(call_id, [])
