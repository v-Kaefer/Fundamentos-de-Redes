from __future__ import annotations

from collections import deque
from threading import Lock

from .models import QueueItem


class QueueFullError(RuntimeError):
    """Raised when local queue is full."""


class QueueStore:
    def __init__(self, max_size: int = 10) -> None:
        self.max_size = max_size
        self._items: deque[QueueItem] = deque()
        self._lock = Lock()

    def put(self, item: QueueItem) -> None:
        with self._lock:
            if len(self._items) >= self.max_size:
                raise QueueFullError("fila cheia")
            self._items.append(item)

    def peek(self) -> QueueItem | None:
        with self._lock:
            if not self._items:
                return None
            return self._items[0]

    def pop(self) -> QueueItem | None:
        with self._lock:
            if not self._items:
                return None
            return self._items.popleft()

    def mark_retry(self) -> QueueItem | None:
        with self._lock:
            if not self._items:
                return None
            self._items[0].retry_total += 1
            return self._items[0]

    def size(self) -> int:
        with self._lock:
            return len(self._items)

    def snapshot(self) -> list[QueueItem]:
        with self._lock:
            return list(self._items)
