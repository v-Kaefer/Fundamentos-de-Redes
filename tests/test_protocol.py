from __future__ import annotations

import unittest

from src.crc_service import calc_crc32
from src.models import DataPacket, NodeInfo
from src.protocol import (
    ACK_FLAG,
    BROADCAST_NAME,
    MISS_FLAG,
    PacketError,
    build_data,
    build_discover,
    build_hello,
    build_token,
    parse_packet,
)


class ProtocolTest(unittest.TestCase):
    def test_build_and_parse_discover(self) -> None:
        node = NodeInfo("A", "127.0.0.1", 6001)
        text = build_discover(node)
        parsed = parse_packet(text)
        self.assertEqual(parsed.kind, "discover")
        self.assertIsNotNone(parsed.node)
        self.assertEqual(parsed.node.nickname, "A")

    def test_build_and_parse_hello(self) -> None:
        node = NodeInfo("B", "127.0.0.1", 6002)
        text = build_hello(node)
        parsed = parse_packet(text)
        self.assertEqual(parsed.kind, "hello")
        self.assertEqual(parsed.node.port_num, 6002)

    def test_parse_data_keeps_colon_in_msg(self) -> None:
        raw_text = "2000:B:A:maquinainexistente:19385749:Oi: teste"
        parsed = parse_packet(raw_text)
        self.assertEqual(parsed.kind, "data")
        self.assertEqual(parsed.data.msg_text, "Oi: teste")

    def test_build_and_parse_data(self) -> None:
        data_pkt = DataPacket(
            src_name="A",
            dst_name=BROADCAST_NAME,
            err_flag=MISS_FLAG,
            crc_value=123,
            msg_text="alo",
        )
        text = build_data(data_pkt)
        parsed = parse_packet(text)
        self.assertEqual(parsed.data.dst_name, BROADCAST_NAME)

    def test_parse_invalid_packet(self) -> None:
        with self.assertRaises(PacketError):
            parse_packet("9999:x")

    def test_build_token(self) -> None:
        self.assertEqual(build_token(), "1000")
        parsed = parse_packet("1000")
        self.assertEqual(parsed.kind, "token")

    def test_crc32_utf8(self) -> None:
        self.assertEqual(calc_crc32("olá"), 1120542206)

    def test_ack_flag_roundtrip(self) -> None:
        data_pkt = DataPacket(
            src_name="A",
            dst_name="B",
            err_flag=ACK_FLAG,
            crc_value=99,
            msg_text="ok",
        )
        parsed = parse_packet(build_data(data_pkt))
        self.assertEqual(parsed.data.err_flag, ACK_FLAG)


if __name__ == "__main__":
    unittest.main()
