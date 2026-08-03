"""
conversation.py
Manages per-session conversation history with a rolling 10-message window.
Resets whenever a new flower is detected from an image upload.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class Message:
    role: str          # "user" | "assistant"
    content: str


class ConversationManager:
    """
    Holds the active flower context, session ID, card metadata, image preview,
    and dialogue history.
    """

    MAX_HISTORY: int = 10  # maximum number of stored messages

    def __init__(self) -> None:
        self._history: list[Message] = []
        self._current_flower: Optional[str] = None
        self._current_summary: Optional[str] = None
        self._current_session_id: Optional[str] = None
        self._current_card: dict = {}
        self._current_image_preview: Optional[str] = None

    # ------------------------------------------------------------------
    # Flower context
    # ------------------------------------------------------------------

    def set_flower(
        self,
        flower_name: str,
        summary: str,
        session_id: Optional[str] = None,
        card: dict = None,
        image_preview: Optional[str] = None,
    ) -> None:
        """Called when a new image is uploaded and classified or session selected."""
        self._current_flower = flower_name
        self._current_summary = summary
        self._current_session_id = session_id or f"session_{flower_name.lower().replace(' ', '_')}_{int(time.time() * 1000)}"
        self._current_card = card or {}
        if image_preview:
            self._current_image_preview = image_preview
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

    @property
    def current_card(self) -> dict:
        return self._current_card

    @property
    def current_image_preview(self) -> Optional[str]:
        return self._current_image_preview

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
        self._current_card = {}
        self._current_image_preview = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _trim(self) -> None:
        """Keep only the last MAX_HISTORY messages."""
        if len(self._history) > self.MAX_HISTORY:
            self._history = self._history[-self.MAX_HISTORY :]


# Singleton instance
conversation_manager = ConversationManager()
