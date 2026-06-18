from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AppConfig:
    nickname: str
    token_delay: float
    error_percent: float
    token_timeout: float
    token_min_gap: float
    unicast_port: int


@dataclass(slots=True)
class NodeInfo:
    nickname: str
    ip_addr: str
    port_num: int
    last_seen: float = 0.0


@dataclass(slots=True)
class DataPacket:
    src_name: str
    dst_name: str
    err_flag: str
    crc_value: int
    msg_text: str


@dataclass(slots=True)
class QueueItem:
    dst_name: str
    msg_text: str
    crc_value: int
    retry_total: int = 0


@dataclass(slots=True)
class RuntimeView:
    local_name: str
    local_ip: str
    local_port: int
    next_name: str
    members: list[str] = field(default_factory=list)
    queue_size: int = 0
    data_in_flight: bool = False
    last_token_at: float = 0.0
