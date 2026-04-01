from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List, Literal, TypedDict

Role = Literal["system", "user", "assistant"]


class ChatMessage(TypedDict):
    role: Role
    content: str


# In-memory history: user_id -> last N messages
_user_memory: Dict[int, Deque[ChatMessage]] = {}
_MAX_HISTORY = 5


def add_message(user_id: int, role: Role, content: str) -> None:
    if user_id not in _user_memory:
        _user_memory[user_id] = deque(maxlen=_MAX_HISTORY)
    _user_memory[user_id].append({"role": role, "content": content})


def get_history(user_id: int) -> List[ChatMessage]:
    history = _user_memory.get(user_id)
    return list(history) if history else []


def clear_history(user_id: int) -> None:
    _user_memory.pop(user_id, None)

