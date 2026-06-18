from __future__ import annotations

from dataclasses import dataclass

from .models import DataPacket, NodeInfo

DISCOVER_CODE = "10"
HELLO_CODE = "20"
TOKEN_CODE = "1000"
DATA_CODE = "2000"

BROADCAST_NAME = "BROADCAST"
ACK_FLAG = "ACK"
NAK_FLAG = "NAK"
MISS_FLAG = "maquinainexistente"


class PacketError(ValueError):
    """Raised when packet content is invalid."""


@dataclass(slots=True)
class ParsedPacket:
    kind: str
    node: NodeInfo | None = None
    data: DataPacket | None = None


def build_discover(node: NodeInfo) -> str:
    return _build_node_pkt(DISCOVER_CODE, node)


def build_hello(node: NodeInfo) -> str:
    return _build_node_pkt(HELLO_CODE, node)


def build_token() -> str:
    return TOKEN_CODE


def build_data(packet: DataPacket) -> str:
    return (
        f"{DATA_CODE}:{packet.src_name}:{packet.dst_name}:{packet.err_flag}:"
        f"{packet.crc_value}:{packet.msg_text}"
    )


def parse_packet(raw_text: str) -> ParsedPacket:
    text = raw_text.strip("\r\n")
    if text == TOKEN_CODE:
        return ParsedPacket(kind="token")

    if text.startswith(f"{DISCOVER_CODE}:"):
        return ParsedPacket(kind="discover", node=_parse_node(text, DISCOVER_CODE))

    if text.startswith(f"{HELLO_CODE}:"):
        return ParsedPacket(kind="hello", node=_parse_node(text, HELLO_CODE))

    if text.startswith(f"{DATA_CODE}:"):
        return ParsedPacket(kind="data", data=_parse_data(text))

    raise PacketError("tipo de pacote desconhecido")


def _build_node_pkt(pkt_code: str, node: NodeInfo) -> str:
    return f"{pkt_code}:{node.nickname}:{node.ip_addr}:{node.port_num}"


def _parse_node(text: str, pkt_code: str) -> NodeInfo:
    parts = text.split(":")
    if len(parts) != 4 or parts[0] != pkt_code:
        raise PacketError("pacote de descoberta invalido")

    nickname = parts[1]
    ip_addr = parts[2]
    try:
        port_num = int(parts[3])
    except ValueError as exc:
        raise PacketError("porta invalida") from exc

    if not nickname or ":" in nickname:
        raise PacketError("apelido invalido")

    return NodeInfo(nickname=nickname, ip_addr=ip_addr, port_num=port_num)


def _parse_data(text: str) -> DataPacket:
    parts = text.split(":", 5)
    if len(parts) != 6 or parts[0] != DATA_CODE:
        raise PacketError("pacote de dados invalido")

    crc_text = parts[4]
    try:
        crc_value = int(crc_text)
    except ValueError as exc:
        raise PacketError("CRC invalido") from exc

    return DataPacket(
        src_name=parts[1],
        dst_name=parts[2],
        err_flag=parts[3],
        crc_value=crc_value,
        msg_text=parts[5],
    )
