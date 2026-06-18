from __future__ import annotations

import argparse
import socket
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import load_config
from src.udp_service import detect_ip


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preflight de teste real")
    parser.add_argument("--config", required=True, help="arquivo de configuracao")
    parser.add_argument(
        "--broadcast",
        default="255.255.255.255",
        help="endereco de broadcast a validar",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    app_cfg = load_config(args.config)
    local_ip = detect_ip()

    print(f"config_ok=1 nome={app_cfg.nickname} porta={app_cfg.unicast_port}")
    print(f"token_delay={app_cfg.token_delay} err_pct={app_cfg.error_percent}")
    print(f"token_timeout={app_cfg.token_timeout} token_gap={app_cfg.token_min_gap}")
    print(f"local_ip={local_ip}")
    print(f"broadcast={args.broadcast}")

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    print(f"log_dir={log_dir.resolve()}")

    bind_udp(6000, "broadcast")
    bind_udp(app_cfg.unicast_port, "unicast")
    probe_bcast(args.broadcast)

    print("preflight_ok=1")
    print("firewall=verifique UDP 6000 e porta unicast liberados")
    return 0


def bind_udp(port_num: int, bind_name: str) -> None:
    test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        test_sock.bind(("", port_num))
        print(f"bind_{bind_name}=ok porta={port_num}")
    finally:
        test_sock.close()


def probe_bcast(bcast_ip: str) -> None:
    test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        test_sock.sendto(b"token-ring-preflight", (bcast_ip, 6000))
        print("send_broadcast=ok")
    finally:
        test_sock.close()


if __name__ == "__main__":
    raise SystemExit(main())
