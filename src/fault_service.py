from __future__ import annotations

import random


class FaultService:
    def __init__(self, error_percent: float, rand_gen: random.Random | None = None) -> None:
        self.error_percent = error_percent
        self.rand_gen = rand_gen or random.Random()

    def maybe_corrupt(self, msg_text: str, is_bcast: bool) -> str:
        if is_bcast:
            return msg_text

        if self.rand_gen.random() * 100.0 >= self.error_percent:
            return msg_text

        return self._corrupt_text(msg_text)

    def _corrupt_text(self, msg_text: str) -> str:
        if not msg_text:
            return "?"

        idx = self.rand_gen.randrange(len(msg_text))
        old_char = msg_text[idx]
        new_char = "X" if old_char != "X" else "Y"
        return msg_text[:idx] + new_char + msg_text[idx + 1 :]
