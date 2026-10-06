"""稳定性守卫配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote_plus


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"缺少必要环境变量：{name}")
    return value


def _int_value(value: object, name: str, default: int, minimum: int = 1) -> int:
    raw = default if value in (None, "") else value
    try:
        parsed = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} 必须是整数") from exc
    if parsed < minimum:
        raise ValueError(f"{name} 不能小于 {minimum}")
    return parsed


@dataclass(frozen=True, slots=True)
class ConnectionSettings:
    postgres_dsn: str
    redis_url: str

    @classmethod
    def from_env(cls) -> "ConnectionSettings":
        pg_user = quote_plus(_required("POSTGRES_USER"))
        pg_password = quote_plus(_required("POSTGRES_PASSWORD"))
        pg_host = os.getenv("POSTGRES_HOST", "postgres").strip() or "postgres"
        pg_port = _int_value(os.getenv("POSTGRES_PORT"), "POSTGRES_PORT", 5432)
        pg_db = quote_plus(_required("POSTGRES_DB"))
        redis_password = quote_plus(_required("REDIS_PASSWORD"))
        redis_host = os.getenv("REDIS_HOST", "redis").strip() or "redis"
        redis_port = _int_value(os.getenv("REDIS_PORT"), "REDIS_PORT", 6379)
        redis_db = _int_value(os.getenv("REDIS_DB"), "REDIS_DB", 0, minimum=0)
        return cls(
            postgres_dsn=(
                f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"
            ),
            redis_url=(
                f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
            ),
        )


@dataclass(frozen=True, slots=True)
class GuardSettings:
    enabled: bool
    store_messages: bool
    deduplicate_messages: bool
    dedup_ttl_seconds: int
    ai_rate_limit_per_minute: int
    message_max_chars: int
    timezone: str

    @classmethod
    def from_config(cls, config: dict) -> "GuardSettings":
        env_limit = _int_value(
            os.getenv("AI_RATE_LIMIT_PER_MINUTE"),
            "AI_RATE_LIMIT_PER_MINUTE",
            10,
        )
        return cls(
            enabled=bool(config.get("enabled", True)),
            store_messages=bool(config.get("store_messages", True)),
            deduplicate_messages=bool(config.get("deduplicate_messages", True)),
            dedup_ttl_seconds=_int_value(
                config.get("dedup_ttl_seconds"), "dedup_ttl_seconds", 86400
            ),
            ai_rate_limit_per_minute=_int_value(
                config.get("ai_rate_limit_per_minute"),
                "ai_rate_limit_per_minute",
                env_limit,
            ),
            message_max_chars=_int_value(
                config.get("message_max_chars"), "message_max_chars", 4000, 200
            ),
            timezone=str(config.get("timezone", os.getenv("TZ", "Asia/Shanghai"))).strip()
            or "Asia/Shanghai",
        )

