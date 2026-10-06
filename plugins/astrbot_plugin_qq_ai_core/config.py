"""从环境变量读取基础设施配置；敏感值不会被日志输出。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote_plus


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"缺少必要环境变量：{name}")
    return value


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"环境变量 {name} 必须是整数") from exc
    if value <= 0:
        raise ValueError(f"环境变量 {name} 必须大于 0")
    return value


@dataclass(frozen=True, slots=True)
class InfrastructureSettings:
    postgres_dsn: str
    postgres_pool_min_size: int
    postgres_pool_max_size: int
    redis_url: str
    redis_pool_max_connections: int

    @classmethod
    def from_env(cls) -> "InfrastructureSettings":
        postgres_user = _required("POSTGRES_USER")
        postgres_password = quote_plus(_required("POSTGRES_PASSWORD"))
        postgres_host = os.getenv("POSTGRES_HOST", "postgres").strip() or "postgres"
        postgres_port = _positive_int("POSTGRES_PORT", 5432)
        postgres_db = _required("POSTGRES_DB")
        pool_min = _positive_int("POSTGRES_POOL_MIN_SIZE", 1)
        pool_max = _positive_int("POSTGRES_POOL_MAX_SIZE", 10)
        if pool_min > pool_max:
            raise ValueError("POSTGRES_POOL_MIN_SIZE 不能大于 POSTGRES_POOL_MAX_SIZE")

        redis_host = os.getenv("REDIS_HOST", "redis").strip() or "redis"
        redis_port = _positive_int("REDIS_PORT", 6379)
        redis_db = int(os.getenv("REDIS_DB", "0"))
        if redis_db < 0:
            raise ValueError("REDIS_DB 不能小于 0")
        redis_password = quote_plus(_required("REDIS_PASSWORD"))

        return cls(
            postgres_dsn=(
                f"postgresql://{quote_plus(postgres_user)}:{postgres_password}"
                f"@{postgres_host}:{postgres_port}/{quote_plus(postgres_db)}"
            ),
            postgres_pool_min_size=pool_min,
            postgres_pool_max_size=pool_max,
            redis_url=f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}",
            redis_pool_max_connections=_positive_int(
                "REDIS_POOL_MAX_CONNECTIONS", 20
            ),
        )

