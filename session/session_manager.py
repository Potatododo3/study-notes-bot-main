"""
Session Manager — tracks per-user state across conversation steps.
"""

import threading
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UserSession:
    chat_id: int
    file_id: Optional[str] = None
    file_name: Optional[str] = None
    file_mime: Optional[str] = None
    subject: Optional[str] = None
    title: Optional[str] = None
    step: str = "idle"           # idle | awaiting_subject | awaiting_title | confirming_title | uploading
    upload_queue: list = field(default_factory=list)


class SessionManager:
    def __init__(self):
        self._sessions: dict[int, UserSession] = {}
        self._lock = threading.Lock()

    def get(self, chat_id: int) -> UserSession:
        with self._lock:
            if chat_id not in self._sessions:
                self._sessions[chat_id] = UserSession(chat_id=chat_id)
            return self._sessions[chat_id]

    def reset(self, chat_id: int):
        with self._lock:
            self._sessions[chat_id] = UserSession(chat_id=chat_id)

    def update(self, chat_id: int, **kwargs):
        session = self.get(chat_id)
        with self._lock:
            for k, v in kwargs.items():
                setattr(session, k, v)


session_manager = SessionManager()
