"""Text-to-speech via edge-tts.

Colombian neural voice (es-CO-SalomeNeural). Free, no API key.
"""
from __future__ import annotations

import os
from typing import AsyncGenerator

TTS_VOICE = os.getenv("TTS_VOICE", "es-CO-SalomeNeural")
TTS_RATE = os.getenv("TTS_RATE", "+0%")


async def stream_tts(text: str) -> AsyncGenerator[bytes, None]:
    """Yield MP3 audio chunks for ``text`` using edge-tts."""
    import edge_tts

    communicate = edge_tts.Communicate(text, voice=TTS_VOICE, rate=TTS_RATE)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            yield chunk["data"]
