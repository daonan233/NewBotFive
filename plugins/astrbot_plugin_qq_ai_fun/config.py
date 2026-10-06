"""插件运行配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote_plus


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"缺少必要环境变量：{name}")
    return value


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"环境变量 {name} 必须是整数") from exc


@dataclass(frozen=True, slots=True)
class ConnectionSettings:
    postgres_dsn: str
    redis_url: str

    @classmethod
    def from_env(cls) -> "ConnectionSettings":
        pg_user = quote_plus(_required("POSTGRES_USER"))
        pg_password = quote_plus(_required("POSTGRES_PASSWORD"))
        pg_host = os.getenv("POSTGRES_HOST", "postgres")
        pg_port = _int_env("POSTGRES_PORT", 5432)
        pg_db = quote_plus(_required("POSTGRES_DB"))
        redis_password = quote_plus(_required("REDIS_PASSWORD"))
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = _int_env("REDIS_PORT", 6379)
        redis_db = _int_env("REDIS_DB", 0)
        return cls(
            postgres_dsn=(
                f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"
            ),
            redis_url=(
                f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
            ),
        )


@dataclass(frozen=True, slots=True)
class FunSettings:
    enabled: bool
    default_think_mode: str
    normal_model: str
    reasoning_model: str
    fast_model: str
    coding_model: str
    lottery_max_winners: int
    lottery_admin_only_start: bool

    @classmethod
    def from_config(cls, config: dict) -> "FunSettings":
        default_mode = str(config.get("default_think_mode", "off")).lower()
        if default_mode not in {"on", "off"}:
            default_mode = "off"
        max_winners = max(1, min(20, int(config.get("lottery_max_winners", 10))))
        return cls(
            enabled=bool(config.get("enabled", True)),
            default_think_mode=default_mode,
            normal_model=(
                str(config.get("normal_model", "")).strip()
                or os.getenv("DEFAULT_MODEL", "").strip()
            ),
            reasoning_model=(
                str(config.get("reasoning_model", "")).strip()
                or os.getenv("SMART_MODEL", "").strip()
            ),
            fast_model=(
                str(config.get("fast_model", "")).strip()
                or os.getenv("FAST_MODEL", "").strip()
            ),
            coding_model=(
                str(config.get("coding_model", "")).strip()
                or os.getenv("CODING_MODEL", "").strip()
            ),
            lottery_max_winners=max_winners,
            lottery_admin_only_start=bool(
                config.get("lottery_admin_only_start", False)
            ),
        )
