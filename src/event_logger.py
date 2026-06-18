from __future__ import annotations

import csv
import time
from pathlib import Path
from threading import Lock


class EventLogger:
    def __init__(self, local_name: str, base_dir: str = "logs") -> None:
        log_dir = Path(base_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        self.local_name = local_name
        self.packet_path = log_dir / f"packets_{local_name}.csv"
        self.ring_path = log_dir / f"ring_{local_name}.csv"
        self._packet_file = self.packet_path.open("w", newline="", encoding="utf-8")
        self._ring_file = self.ring_path.open("w", newline="", encoding="utf-8")
        self._packet_csv = csv.writer(self._packet_file)
        self._ring_csv = csv.writer(self._ring_file)
        self._lock = Lock()
        self._packet_csv.writerow(
            [
                "timestamp",
                "local",
                "event",
                "type",
                "direction",
                "src",
                "dst",
                "control",
                "crc",
                "message_preview",
                "next_hop_ip",
                "next_hop_port",
            ]
        )
        self._ring_csv.writerow(
            [
                "timestamp",
                "local",
                "members",
                "successor",
                "queue_size",
                "last_token_seen",
                "last_event",
            ]
        )

    def show(self, msg_text: str) -> None:
        with self._lock:
            print(msg_text, flush=True)

    def log_packet(
        self,
        event_name: str,
        pkt_type: str,
        direction: str,
        src_name: str = "",
        dst_name: str = "",
        ctrl_flag: str = "",
        crc_value: int | str = "",
        msg_text: str = "",
        next_ip: str = "",
        next_port: int | str = "",
    ) -> None:
        with self._lock:
            self._packet_csv.writerow(
                [
                    self._stamp(),
                    self.local_name,
                    event_name,
                    pkt_type,
                    direction,
                    src_name,
                    dst_name,
                    ctrl_flag,
                    crc_value,
                    msg_text[:80],
                    next_ip,
                    next_port,
                ]
            )
            self._packet_file.flush()

    def log_ring(
        self,
        members_text: str,
        next_name: str,
        queue_size: int,
        last_token_at: float,
        event_name: str,
    ) -> None:
        with self._lock:
            self._ring_csv.writerow(
                [
                    self._stamp(),
                    self.local_name,
                    members_text,
                    next_name,
                    queue_size,
                    f"{last_token_at:.3f}",
                    event_name,
                ]
            )
            self._ring_file.flush()

    def close(self) -> None:
        with self._lock:
            self._packet_file.close()
            self._ring_file.close()

    def _stamp(self) -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
