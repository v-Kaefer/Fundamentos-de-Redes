from __future__ import annotations

import socket
import threading
import time

from .crc_service import calc_crc32
from .discovery import DiscoveryService
from .event_logger import EventLogger
from .fault_service import FaultService
from .models import AppConfig, DataPacket, NodeInfo, QueueItem, RuntimeView
from .protocol import (
    ACK_FLAG,
    BROADCAST_NAME,
    DATA_CODE,
    MISS_FLAG,
    NAK_FLAG,
    PacketError,
    build_data,
    build_token,
    parse_packet,
)
from .queue_store import QueueFullError, QueueStore
from .ring_state import RingState
from .token_state import TokenState
from .udp_service import UdpService, detect_ip


class NodeRuntime:
    def __init__(
        self,
        app_cfg: AppConfig,
        broadcast_addr: str = "255.255.255.255",
        udp_service: UdpService | None = None,
        event_logger: EventLogger | None = None,
    ) -> None:
        local_ip = detect_ip()
        self.app_cfg = app_cfg
        self.local_node = NodeInfo(
            nickname=app_cfg.nickname,
            ip_addr=local_ip,
            port_num=app_cfg.unicast_port,
        )
        self.udp_service = udp_service or UdpService(
            unicast_port=app_cfg.unicast_port,
            broadcast_addr=broadcast_addr,
        )
        self.event_logger = event_logger or EventLogger(app_cfg.nickname)
        self.ring_state = RingState(app_cfg.nickname)
        self.ring_state.upsert_node(self.local_node)
        self.ring_state.apply_order()
        self.token_state = TokenState()
        self.queue_store = QueueStore(max_size=10)
        self.fault_service = FaultService(app_cfg.error_percent)
        self.discovery = DiscoveryService(
            local_node=self.local_node,
            ring_state=self.ring_state,
            udp_service=self.udp_service,
            event_logger=self.event_logger,
        )
        self.stop_event = threading.Event()
        self.thread_list: list[threading.Thread] = []

    def start(self, discover_wait: float = 2.0) -> None:
        self._start_thread(self._run_bcast, "broadcast_listener")
        self._start_thread(self._run_uni, "unicast_listener")
        self._start_thread(self._run_watch, "token_watch")
        self.discovery.send_discover()
        self.event_logger.show(
            f"[{self.local_node.nickname}] descoberta iniciada por {discover_wait:.1f}s"
        )
        time.sleep(discover_wait)
        self._apply_topology("INIT_RING")
        if self.ring_state.is_leader():
            self.event_logger.show(
                f"[{self.local_node.nickname}] lider inicial, gerando primeiro token"
            )
            self.send_token()

    def stop(self) -> None:
        if self.stop_event.is_set():
            return
        self.stop_event.set()
        for worker in self.thread_list:
            worker.join(timeout=1.0)
        self.udp_service.close()
        self.event_logger.close()

    def queue_unicast(self, dst_name: str, msg_text: str) -> None:
        item = QueueItem(
            dst_name=dst_name,
            msg_text=msg_text,
            crc_value=calc_crc32(msg_text),
        )
        self.queue_store.put(item)
        self.event_logger.show(
            f"[{self.local_node.nickname}] mensagem enfileirada para {dst_name}"
        )
        self._log_ring("QUEUE_ADD")

    def queue_bcast(self, msg_text: str) -> None:
        self.queue_unicast(BROADCAST_NAME, msg_text)

    def drop_next_token(self) -> None:
        self.token_state.arm_drop()
        self.event_logger.show(f"[{self.local_node.nickname}] proximo token sera descartado")

    def insert_token(self) -> None:
        self.token_state.add_manual()
        self.event_logger.show(f"[{self.local_node.nickname}] token manual inserido")
        self.send_token()

    def get_queue_lines(self) -> list[str]:
        items = self.queue_store.snapshot()
        if not items:
            return ["(fila vazia)"]
        return [
            f"{idx + 1}. dst={item.dst_name} retry={item.retry_total} msg={item.msg_text}"
            for idx, item in enumerate(items)
        ]

    def get_ring_text(self) -> str:
        return self.ring_state.snapshot_text()

    def get_state_view(self) -> RuntimeView:
        last_token_at, data_in_flight = self.token_state.view_state()
        next_node = self.ring_state.get_next_node()
        return RuntimeView(
            local_name=self.local_node.nickname,
            local_ip=self.local_node.ip_addr,
            local_port=self.local_node.port_num,
            next_name=next_node.nickname if next_node else "",
            members=self.ring_state.get_members(),
            queue_size=self.queue_store.size(),
            data_in_flight=data_in_flight,
            last_token_at=last_token_at,
        )

    def send_token(self) -> None:
        if self.stop_event.is_set():
            return
        next_node = self.ring_state.get_next_node()
        if next_node is None:
            self.event_logger.show(f"[{self.local_node.nickname}] sem sucessor para token")
            return

        raw_text = build_token()
        try:
            self.udp_service.send_uni(raw_text, next_node.ip_addr, next_node.port_num)
        except OSError:
            if self.stop_event.is_set():
                return
            raise
        now_time = time.monotonic()
        self.token_state.note_send(now_time)
        self.event_logger.log_packet(
            "SEND_TOKEN",
            "TOKEN",
            "OUT",
            src_name=self.local_node.nickname,
            next_ip=next_node.ip_addr,
            next_port=next_node.port_num,
        )
        self._log_ring("SEND_TOKEN")

    def _start_thread(self, target_fn, thread_name: str) -> None:
        worker = threading.Thread(target=target_fn, name=thread_name, daemon=True)
        worker.start()
        self.thread_list.append(worker)

    def _run_bcast(self) -> None:
        while not self.stop_event.is_set():
            try:
                raw_text, _addr = self.udp_service.recv_bcast()
            except socket.timeout:
                continue
            except OSError:
                break

            self._handle_bcast_text(raw_text)

    def _run_uni(self) -> None:
        while not self.stop_event.is_set():
            try:
                raw_text, _addr = self.udp_service.recv_uni()
            except socket.timeout:
                continue
            except OSError:
                break

            self._handle_uni_text(raw_text)

    def _run_watch(self) -> None:
        while not self.stop_event.wait(0.5):
            if not self.ring_state.is_leader():
                continue

            now_time = time.monotonic()
            if self.token_state.should_rebuild(now_time, self.app_cfg.token_timeout):
                self.event_logger.show(
                    f"[{self.local_node.nickname}] token perdido, regenerando"
                )
                self.send_token()

    def _handle_bcast_text(self, raw_text: str) -> None:
        try:
            parsed = parse_packet(raw_text)
        except PacketError:
            return

        if parsed.kind == "discover" and parsed.node is not None:
            self.event_logger.log_packet(
                "RECV_DISCOVER",
                "DISCOVER",
                "IN",
                src_name=parsed.node.nickname,
            )
            self.discovery.handle_discover(parsed.node)
            return

        if parsed.kind == "hello" and parsed.node is not None:
            self.event_logger.log_packet(
                "RECV_HELLO",
                "HELLO",
                "IN",
                src_name=parsed.node.nickname,
            )
            self.discovery.handle_hello(parsed.node)

    def _handle_uni_text(self, raw_text: str) -> None:
        try:
            parsed = parse_packet(raw_text)
        except PacketError:
            return

        if parsed.kind == "token":
            self._handle_token()
            return

        if parsed.kind == "data" and parsed.data is not None:
            self._handle_data(parsed.data)

    def _handle_token(self) -> None:
        now_time = time.monotonic()
        if self.ring_state.is_leader() and self.token_state.check_dup(
            now_time, self.app_cfg.token_min_gap
        ):
            self.event_logger.show(
                f"[{self.local_node.nickname}] token duplicado detectado e descartado"
            )
            self.event_logger.log_packet(
                "DROP_TOKEN",
                "TOKEN",
                "IN",
                src_name=self.local_node.nickname,
            )
            return

        self.token_state.note_token(now_time)
        self.event_logger.log_packet(
            "RECV_TOKEN",
            "TOKEN",
            "IN",
            src_name=self.local_node.nickname,
        )
        self._log_ring("RECV_TOKEN")

        if self.token_state.consume_drop():
            self.event_logger.show(f"[{self.local_node.nickname}] token descartado por comando")
            self.event_logger.log_packet(
                "DROP_TOKEN",
                "TOKEN",
                "IN",
                src_name=self.local_node.nickname,
            )
            self._log_ring("DROP_TOKEN")
            return

        if self.token_state.is_flight():
            self.event_logger.show(
                f"[{self.local_node.nickname}] token extra recebido com dado pendente"
            )
            self.event_logger.log_packet(
                "DROP_TOKEN",
                "TOKEN",
                "IN",
                src_name=self.local_node.nickname,
            )
            return

        self._apply_topology("RING_UPDATE")
        time.sleep(self.app_cfg.token_delay)

        if self.queue_store.peek() is not None:
            self._send_head()
        else:
            self.send_token()

    def _handle_data(self, data_pkt: DataPacket) -> None:
        self.token_state.note_ring(time.monotonic())
        self.event_logger.log_packet(
            "RECV_DATA",
            DATA_CODE,
            "IN",
            src_name=data_pkt.src_name,
            dst_name=data_pkt.dst_name,
            ctrl_flag=data_pkt.err_flag,
            crc_value=data_pkt.crc_value,
            msg_text=data_pkt.msg_text,
        )

        if data_pkt.src_name == self.local_node.nickname:
            self._handle_return(data_pkt)
            return

        if data_pkt.dst_name == BROADCAST_NAME:
            self.event_logger.show(
                f"[{self.local_node.nickname}] broadcast de {data_pkt.src_name}: {data_pkt.msg_text}"
            )
            self._forward_data(data_pkt, "FORWARD_DATA")
            return

        if data_pkt.dst_name == self.local_node.nickname:
            recv_crc = calc_crc32(data_pkt.msg_text)
            data_pkt.err_flag = ACK_FLAG if recv_crc == data_pkt.crc_value else NAK_FLAG
            self.event_logger.show(
                f"[{self.local_node.nickname}] msg de {data_pkt.src_name}: {data_pkt.msg_text}"
            )
            self._forward_data(data_pkt, data_pkt.err_flag)
            return

        self._forward_data(data_pkt, "FORWARD_DATA")

    def _handle_return(self, data_pkt: DataPacket) -> None:
        queue_item = self.queue_store.peek()
        self.token_state.set_flight(False)
        if queue_item is None:
            self.event_logger.show(
                f"[{self.local_node.nickname}] pacote retornou sem item na fila"
            )
            self.send_token()
            return

        if data_pkt.dst_name == BROADCAST_NAME:
            self.queue_store.pop()
            self.event_logger.show(
                f"[{self.local_node.nickname}] broadcast concluido: {data_pkt.msg_text}"
            )
            self._log_ring("BCAST_DONE")
            self.send_token()
            return

        if data_pkt.err_flag == ACK_FLAG:
            self.queue_store.pop()
            self.event_logger.show(
                f"[{self.local_node.nickname}] ACK de {data_pkt.dst_name}"
            )
            self._log_ring("ACK")
            self.send_token()
            return

        if data_pkt.err_flag == NAK_FLAG:
            if queue_item.retry_total == 0:
                self.queue_store.mark_retry()
                self.event_logger.show(
                    f"[{self.local_node.nickname}] NAK recebido, retransmissao agendada"
                )
                self._log_ring("NAK_RETRY")
            else:
                self.queue_store.pop()
                self.event_logger.show(
                    f"[{self.local_node.nickname}] NAK repetido, mensagem descartada"
                )
                self._log_ring("NAK_DROP")
            self.send_token()
            return

        self.queue_store.pop()
        self.event_logger.show(
            f"[{self.local_node.nickname}] destino {data_pkt.dst_name} inexistente"
        )
        self._log_ring("MISS_DST")
        self.send_token()

    def _send_head(self) -> None:
        if self.stop_event.is_set():
            return
        queue_item = self.queue_store.peek()
        next_node = self.ring_state.get_next_node()
        if queue_item is None or next_node is None:
            self.send_token()
            return

        is_bcast = queue_item.dst_name == BROADCAST_NAME
        msg_text = self.fault_service.maybe_corrupt(queue_item.msg_text, is_bcast)
        data_pkt = DataPacket(
            src_name=self.local_node.nickname,
            dst_name=queue_item.dst_name,
            err_flag=MISS_FLAG,
            crc_value=queue_item.crc_value,
            msg_text=msg_text,
        )
        raw_text = build_data(data_pkt)
        try:
            self.udp_service.send_uni(raw_text, next_node.ip_addr, next_node.port_num)
        except OSError:
            if self.stop_event.is_set():
                return
            raise
        self.token_state.set_flight(True)
        self.token_state.note_send(time.monotonic())
        self.event_logger.log_packet(
            "SEND_DATA",
            DATA_CODE,
            "OUT",
            src_name=data_pkt.src_name,
            dst_name=data_pkt.dst_name,
            ctrl_flag=data_pkt.err_flag,
            crc_value=data_pkt.crc_value,
            msg_text=data_pkt.msg_text,
            next_ip=next_node.ip_addr,
            next_port=next_node.port_num,
        )
        self.event_logger.show(
            f"[{self.local_node.nickname}] enviando para {queue_item.dst_name}: {queue_item.msg_text}"
        )
        self._log_ring("SEND_DATA")

    def _forward_data(self, data_pkt: DataPacket, event_name: str) -> None:
        if self.stop_event.is_set():
            return
        next_node = self.ring_state.get_next_node()
        if next_node is None:
            return

        raw_text = build_data(data_pkt)
        try:
            self.udp_service.send_uni(raw_text, next_node.ip_addr, next_node.port_num)
        except OSError:
            if self.stop_event.is_set():
                return
            raise
        self.token_state.note_send(time.monotonic())
        self.event_logger.log_packet(
            event_name,
            DATA_CODE,
            "OUT",
            src_name=data_pkt.src_name,
            dst_name=data_pkt.dst_name,
            ctrl_flag=data_pkt.err_flag,
            crc_value=data_pkt.crc_value,
            msg_text=data_pkt.msg_text,
            next_ip=next_node.ip_addr,
            next_port=next_node.port_num,
        )

    def _apply_topology(self, event_name: str) -> None:
        if self.ring_state.apply_if_dirty():
            self.event_logger.show(
                f"[{self.local_node.nickname}] anel: {self.ring_state.snapshot_text()}"
            )
            self._log_ring(event_name)

    def _log_ring(self, event_name: str) -> None:
        last_token_at, _data_in_flight = self.token_state.view_state()
        next_node = self.ring_state.get_next_node()
        self.event_logger.log_ring(
            members_text=self.ring_state.snapshot_text(),
            next_name=next_node.nickname if next_node else "",
            queue_size=self.queue_store.size(),
            last_token_at=last_token_at,
            event_name=event_name,
        )
