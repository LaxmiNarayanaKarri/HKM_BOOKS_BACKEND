from __future__ import annotations

import threading
import time
from typing import Any, Callable


class TTLCache:
    def __init__(self, ttl_seconds: int = 120) -> None:
        self._ttl_seconds = ttl_seconds
        self._entries: dict[str, tuple[float, Any]] = {}
        self._lock = threading.RLock()

    def get_or_set(self, key: str, factory: Callable[[], Any]) -> Any:
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None and entry[0] > now:
                return entry[1]

        value = factory()
        with self._lock:
            self._entries[key] = (time.monotonic() + self._ttl_seconds, value)
        return value
