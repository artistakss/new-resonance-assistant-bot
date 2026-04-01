from __future__ import annotations

import os
from typing import Any
from typing import List, Optional, TypedDict

import httpx


class ChatMessage(TypedDict):
    role: str
    content: str


class OpenAIChatError(RuntimeError):
    pass


def _get_openai_key() -> Optional[str]:
    return os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")


def _get_openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


async def chat_completion(messages: List[ChatMessage]) -> str:
    api_key = _get_openai_key()
    if not api_key:
        raise OpenAIChatError("OPENAI_API_KEY is not set")

    model = _get_openai_model()

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.7,
                },
            )
    except Exception as exc:
        raise OpenAIChatError("⚠️ Ошибка при обращении к AI. Попробуй позже.") from exc

    if resp.status_code >= 400:
        raise OpenAIChatError("⚠️ Ошибка при обращении к AI. Попробуй позже.")

    data: Any = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        raise OpenAIChatError("⚠️ Ошибка при обращении к AI. Попробуй позже.") from exc

