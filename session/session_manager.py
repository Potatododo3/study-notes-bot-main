"""
Session Manager — tracks per-user state across conversation steps.
"""

import json
import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


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
        self._path = os.environ.get("SESSION_STORAGE_PATH", "data/sessions.json")
        self._load()

    def _load(self):
        try:
            with open(self._path, "r", encoding="utf-8") as state_file:
                saved = json.load(state_file)
            for chat_id, values in saved.items():
                values["chat_id"] = int(chat_id)
                # An interrupted upload must be retryable after a process restart.
                if values.get("step") == "uploading":
                    values["step"] = "file_received"
                self._sessions[int(chat_id)] = UserSession(**values)
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError, AttributeError):
            logger.exception("Could not load saved sessions from %s", self._path)

    def _save(self):
        directory = os.path.dirname(os.path.abspath(self._path))
        os.makedirs(directory, exist_ok=True)
        temporary_path = self._path + ".tmp"
        with open(temporary_path, "w", encoding="utf-8") as state_file:
            json.dump(
                {str(key): vars(value) for key, value in self._sessions.items()},
                state_file,
                ensure_ascii=False,
            )
            state_file.flush()
            os.fsync(state_file.fileno())
        os.replace(temporary_path, self._path)

    def get(self, chat_id: int) -> UserSession:
        with self._lock:
            if chat_id not in self._sessions:
                self._sessions[chat_id] = UserSession(chat_id=chat_id)
                self._save()
            return self._sessions[chat_id]

    def reset(self, chat_id: int):
        with self._lock:
            self._sessions[chat_id] = UserSession(chat_id=chat_id)
            self._save()

    def update(self, chat_id: int, **kwargs):
        session = self.get(chat_id)
        with self._lock:
            for k, v in kwargs.items():
                setattr(session, k, v)
            self._save()


session_manager = SessionManager()
