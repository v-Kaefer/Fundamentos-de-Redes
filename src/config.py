from __future__ import annotations

from pathlib import Path

from .models import AppConfig


class ConfigError(ValueError):
    """Raised when config content is invalid."""


def load_config(file_path: str | Path) -> AppConfig:
    path_obj = Path(file_path)
    raw_lines = path_obj.read_text(encoding="utf-8").splitlines()
    lines = [line.strip() for line in raw_lines if line.strip()]
    if len(lines) != 6:
        raise ConfigError("config deve conter 6 linhas nao vazias")

    nickname = lines[0]
    if ":" in nickname or not nickname:
        raise ConfigError("apelido invalido")

    try:
        token_delay = float(lines[1])
        error_percent = float(lines[2])
        token_timeout = float(lines[3])
        token_min_gap = float(lines[4])
        unicast_port = int(lines[5])
    except ValueError as exc:
        raise ConfigError("valores numericos invalidos") from exc

    if not 0.0 <= error_percent <= 100.0:
        raise ConfigError("probabilidade de erro deve estar entre 0 e 100")
    if token_delay < 0.0 or token_timeout <= 0.0 or token_min_gap < 0.0:
        raise ConfigError("tempos invalidos")
    if not 1 <= unicast_port <= 65535:
        raise ConfigError("porta invalida")

    return AppConfig(
        nickname=nickname,
        token_delay=token_delay,
        error_percent=error_percent,
        token_timeout=token_timeout,
        token_min_gap=token_min_gap,
        unicast_port=unicast_port,
    )
