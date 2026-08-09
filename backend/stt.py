"""Speech-to-text via Groq Whisper (whisper-large-v3).

Free tier, strong es-CO accuracy. Free-choice per challenge rules.
"""
from __future__ import annotations

import os
from typing import Optional

from groq import Groq

STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3")


class STTClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY required for STT")
        self._client = Groq(api_key=self.api_key)

    def transcribe(self, filename: str, data: bytes) -> str:
        result = self._client.audio.transcriptions.create(
            file=(filename, data),
            model=STT_MODEL,
            language="es",
        )
        return (getattr(result, "text", "") or "").strip()
