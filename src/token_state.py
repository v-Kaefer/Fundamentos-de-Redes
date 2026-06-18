from __future__ import annotations

from threading import Lock


class TokenState:
    def __init__(self) -> None:
        self.last_token_at = 0.0
        self.last_send_at = 0.0
        self.last_ring_at = 0.0
        self.drop_next = False
        self.manual_count = 0
        self.data_in_flight = False
        self._lock = Lock()

    def check_dup(self, now_time: float, min_gap: float) -> bool:
        with self._lock:
            return self.last_token_at > 0.0 and (now_time - self.last_token_at) < min_gap

    def note_ring(self, now_time: float) -> None:
        with self._lock:
            self.last_ring_at = now_time

    def note_token(self, now_time: float) -> None:
        with self._lock:
            self.last_token_at = now_time
            self.last_ring_at = now_time

    def note_send(self, now_time: float) -> None:
        with self._lock:
            self.last_send_at = now_time
            self.last_ring_at = now_time

    def set_flight(self, is_active: bool) -> None:
        with self._lock:
            self.data_in_flight = is_active

    def is_flight(self) -> bool:
        with self._lock:
            return self.data_in_flight

    def arm_drop(self) -> None:
        with self._lock:
            self.drop_next = True

    def consume_drop(self) -> bool:
        with self._lock:
            if not self.drop_next:
                return False
            self.drop_next = False
            return True

    def add_manual(self) -> None:
        with self._lock:
            self.manual_count += 1

    def should_rebuild(self, now_time: float, token_timeout: float) -> bool:
        with self._lock:
            base_time = max(self.last_ring_at, self.last_token_at)
            if base_time == 0.0:
                return False
            return (now_time - base_time) >= token_timeout

    def view_state(self) -> tuple[float, bool]:
        with self._lock:
            return self.last_token_at, self.data_in_flight
