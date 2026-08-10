import os
from typing import Any, Dict, List, Optional

from groq import Groq


class LLMClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        if model is None:
            model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Groq API key is required. Pass api_key=... or set GROQ_API_KEY env var."
            )
        self.model = model
        self.client = Groq(api_key=self.api_key)
        self.last_usage: Dict[str, int] = {}

    def _call(self, messages: List[Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
        last_exc = None
        for attempt in range(3):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    **kwargs,
                )
                choice = response.choices[0]
                usage = response.usage
                return {
                    "content": choice.message.content,
                    "usage": {
                        "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                        "completion_tokens": getattr(usage, "completion_tokens", 0),
                        "total_tokens": getattr(usage, "total_tokens", 0),
                    },
                }
            except Exception as exc:
                last_exc = exc
                msg = str(exc).lower()
                if "rate" in msg or "429" in msg or "limit" in msg:
                    import time
                    time.sleep(2 ** attempt)  # exponential backoff
                    continue
                raise
        raise last_exc

    def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> Dict[str, Any]:
        return self._call(messages, temperature=temperature, max_tokens=max_tokens)

    def generate(
        self,
        transcript: str,
        context: str = "",
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        from backend.prompts import SYSTEM_PROMPT, GREETING_INSTRUCTION
        is_greeting = not transcript.strip()
        system_prompt = SYSTEM_PROMPT + GREETING_INSTRUCTION if is_greeting else SYSTEM_PROMPT
        conversation: List[Dict[str, Any]] = []
        for turn in history or []:
            t = (turn.get("transcript") or "").strip()
            r = (turn.get("response") or "").strip()
            if t:
                conversation.append({"role": "user", "content": t})
            if r:
                conversation.append({"role": "assistant", "content": r})
        conversation.append({"role": "user", "content": transcript or "Hola"})
        messages = build_messages(
            system_prompt,
            conversation,
            context_docs=[context] if context else None,
        )
        result = self._call(messages, temperature=0.3, max_tokens=500)
        self.last_usage = result.get("usage", {})
        return result.get("content", "")


def build_messages(
    system_prompt: str,
    conversation: List[Dict[str, Any]],
    context_docs: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    if context_docs:
        joined = "\n".join(f"- {doc}" for doc in context_docs)
        system_content = f"{system_prompt}\n\nContext:\n{joined}"
    else:
        system_content = system_prompt
    return [{"role": "system", "content": system_content}, *conversation]
