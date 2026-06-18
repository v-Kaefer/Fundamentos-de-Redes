from __future__ import annotations

import zlib


def calc_crc32(msg_text: str) -> int:
    msg_bytes = msg_text.encode("utf-8")
    return zlib.crc32(msg_bytes) & 0xFFFFFFFF
