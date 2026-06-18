from __future__ import annotations

import argparse

from .config import load_config
from .console_ui import ConsoleUI
from .node_runtime import NodeRuntime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simulador Token Ring UDP")
    parser.add_argument("--config", required=True, help="arquivo de configuracao")
    parser.add_argument(
        "--broadcast",
        default="255.255.255.255",
        help="endereco de broadcast",
    )
    parser.add_argument(
        "--discover-wait",
        type=float,
        default=2.0,
        help="janela inicial de descoberta em segundos",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    app_cfg = load_config(args.config)
    runtime = NodeRuntime(app_cfg, broadcast_addr=args.broadcast)
    try:
        runtime.start(discover_wait=args.discover_wait)
        ConsoleUI(runtime).run()
    finally:
        runtime.stop()


if __name__ == "__main__":
    main()
