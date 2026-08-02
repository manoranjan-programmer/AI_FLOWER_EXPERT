"""
conversation.py
Manages per-session conversation history with a rolling 10-message window.
Resets whenever a new flower is detected from an image upload.
"""

from __future__ import annotations

from typing import Optional
from dataclasses import dataclass


@dataclass
class Message:
    role: str          # "user" | "assistant"
    content: str


import time

class ConversationManager:
    """
    Holds the active flower context, session ID, and the last N turns of dialogue.
    A single global instance is shared across all requests (single-user app).
    For multi-user deployments, swap this for a session-keyed dict or Redis.
    """

    MAX_HISTORY: int = 10  # maximum number of stored messages (user + assistant combined)

    def __init__(self) -> None:
        self._history: list[Message] = []
        self._current_flower: Optional[str] = None
        self._current_summary: Optional[str] = None
        self._current_session_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Flower context
    # ------------------------------------------------------------------

    def set_flower(self, flower_name: str, summary: str, session_id: Optional[str] = None) -> None:
        """Called when a new image is uploaded and classified."""
        self._current_flower = flower_name
        self._current_summary = summary
        self._current_session_id = session_id or f"session_{flower_name.lower().replace(' ', '_')}_{int(time.time() * 1000)}"
        self._history.clear()           # fresh conversation for each new flower

    @property
    def current_flower(self) -> Optional[str]:
        return self._current_flower

    @property
    def current_summary(self) -> Optional[str]:
        return self._current_summary

    @property
    def current_session_id(self) -> Optional[str]:
        return self._current_session_id

    def has_flower(self) -> bool:
        return self._current_flower is not None

    # ------------------------------------------------------------------
    # History management
    # ------------------------------------------------------------------

    def add_user_message(self, content: str) -> None:
        self._history.append(Message(role="user", content=content))
        self._trim()

    def add_assistant_message(self, content: str) -> None:
        self._history.append(Message(role="assistant", content=content))
        self._trim()

    def get_history(self) -> list[Message]:
        return list(self._history)

    def get_history_as_dicts(self) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in self._history]

    def clear(self) -> None:
        self._history.clear()
        self._current_flower = None
        self._current_summary = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _trim(self) -> None:
        """Keep only the last MAX_HISTORY messages."""
        if len(self._history) > self.MAX_HISTORY:
            self._history = self._history[-self.MAX_HISTORY :]


# ---------------------------------------------------------------------------
# Module-level singleton – imported by other modules
# ---------------------------------------------------------------------------
conversation_manager = ConversationManager()
