"""
In-memory session manager.

Tracks active sessions and per-user request history without any persistence layer.
"""

import time
import threading
from collections import defaultdict
from typing import Dict, List, Any


class SessionManager:
    """Lightweight in-memory session tracker."""

    _MAX_HISTORY = 50  # keep last N requests per user to cap memory usage

    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._lock = threading.Lock()

    # ── Session lifecycle ─────────────────────────────────────────────────────

    def create_session(self, session_id: str, user_id: str) -> None:
        with self._lock:
            self._sessions[session_id] = {
                "user_id": user_id,
                "created_at": time.time(),
                "last_active": time.time(),
            }

    def get_session(self, session_id: str) -> Dict[str, Any] | None:
        with self._lock:
            return self._sessions.get(session_id)

    # ── Request tracking ──────────────────────────────────────────────────────

    def record_request(self, user_id: str, sector: str) -> None:
        entry = {
            "sector": sector,
            "timestamp": time.time(),
        }
        with self._lock:
            history = self._history[user_id]
            history.append(entry)
            # Trim to cap
            if len(history) > self._MAX_HISTORY:
                self._history[user_id] = history[-self._MAX_HISTORY:]

    def get_history(self, user_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._history.get(user_id, []))

    # ── Stats ─────────────────────────────────────────────────────────────────

    def active_session_count(self) -> int:
        with self._lock:
            return len(self._sessions)
