from __future__ import annotations

from .event_logger import EventLogger
from .models import NodeInfo
from .protocol import build_discover, build_hello
from .ring_state import RingState
from .udp_service import UdpService


class DiscoveryService:
    def __init__(
        self,
        local_node: NodeInfo,
        ring_state: RingState,
        udp_service: UdpService,
        event_logger: EventLogger,
    ) -> None:
        self.local_node = local_node
        self.ring_state = ring_state
        self.udp_service = udp_service
        self.event_logger = event_logger

    def send_discover(self) -> None:
        raw_text = build_discover(self.local_node)
        self.udp_service.send_bcast(raw_text)
        self.event_logger.log_packet(
            "SEND_DISCOVER",
            "DISCOVER",
            "OUT",
            src_name=self.local_node.nickname,
            next_ip=self.udp_service.broadcast_addr,
            next_port=self.udp_service.broadcast_port,
        )

    def send_hello(self) -> None:
        raw_text = build_hello(self.local_node)
        self.udp_service.send_bcast(raw_text)
        self.event_logger.log_packet(
            "SEND_HELLO",
            "HELLO",
            "OUT",
            src_name=self.local_node.nickname,
            next_ip=self.udp_service.broadcast_addr,
            next_port=self.udp_service.broadcast_port,
        )

    def handle_discover(self, remote_node: NodeInfo) -> None:
        if self._is_local(remote_node):
            return
        self.ring_state.upsert_node(remote_node)
        self.send_hello()

    def handle_hello(self, remote_node: NodeInfo) -> None:
        if self._is_local(remote_node):
            return
        self.ring_state.upsert_node(remote_node)

    def _is_local(self, remote_node: NodeInfo) -> bool:
        return (
            remote_node.nickname == self.local_node.nickname
            and remote_node.port_num == self.local_node.port_num
        )
