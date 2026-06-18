from __future__ import annotations

import socket


class UdpService:
    def __init__(
        self,
        unicast_port: int,
        broadcast_port: int = 6000,
        broadcast_addr: str = "255.255.255.255",
    ) -> None:
        self.unicast_port = unicast_port
        self.broadcast_port = broadcast_port
        self.broadcast_addr = broadcast_addr
        self.bcast_sock = self._make_bcast_sock()
        self.uni_sock = self._make_uni_sock()

    def send_bcast(self, msg_text: str) -> None:
        data = msg_text.encode("utf-8")
        self.bcast_sock.sendto(data, (self.broadcast_addr, self.broadcast_port))

    def send_uni(self, msg_text: str, ip_addr: str, port_num: int) -> None:
        data = msg_text.encode("utf-8")
        self.uni_sock.sendto(data, (ip_addr, port_num))

    def recv_bcast(self, buf_size: int = 8192) -> tuple[str, tuple[str, int]]:
        data, addr = self.bcast_sock.recvfrom(buf_size)
        return data.decode("utf-8", errors="replace"), addr

    def recv_uni(self, buf_size: int = 8192) -> tuple[str, tuple[str, int]]:
        data, addr = self.uni_sock.recvfrom(buf_size)
        return data.decode("utf-8", errors="replace"), addr

    def close(self) -> None:
        self.bcast_sock.close()
        self.uni_sock.close()

    def _make_bcast_sock(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except (AttributeError, OSError):
            pass
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("", self.broadcast_port))
        sock.settimeout(0.5)
        return sock

    def _make_uni_sock(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", self.unicast_port))
        sock.settimeout(0.5)
        return sock


def detect_ip() -> str:
    probe_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe_sock.connect(("8.8.8.8", 80))
        return probe_sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        probe_sock.close()
