import os
import time
from typing import Any, Dict, List, Optional

from groq import Groq


class LLMClient:
    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Groq API key is required. Pass api_key=... or set GROQ_API_KEY env var."
            )
        self.model = model
        self.client = Groq(api_key=self.api_key)

    def _call(self, messages: List[Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
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

    def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> Dict[str, Any]:
        return self._call(messages, temperature=temperature, max_tokens=max_tokens)


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


def generate_response(
    client: LLMClient,
    system_prompt: str,
    conversation: List[Dict[str, Any]],
    context_docs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    messages = build_messages(system_prompt, conversation, context_docs)
    start = time.time()
    result = client._call(messages)
    latency = time.time() - start
    usage = result.get("usage", {}) or {}
    return {
        "response": result.get("content", ""),
        "tokens": {
            "input": usage.get("prompt_tokens", 0),
            "output": usage.get("completion_tokens", 0),
            "total": usage.get("total_tokens", 0),
        },
        "latency": latency,
    }
