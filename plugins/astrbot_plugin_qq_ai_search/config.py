"""联网搜索配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote_plus


def _bounded(value: object, default: int, low: int, high: int) -> int:
    try:
        parsed = int(default if value in (None, "") else value)
    except (TypeError, ValueError):
        parsed = default
    return max(low, min(high, parsed))


@dataclass(frozen=True, slots=True)
class SearchSettings:
    enabled: bool
    provider: str
    api_key: str
    api_base: str
    max_results: int
    timeout_seconds: int
    rate_limit_per_minute: int
    redis_url: str

    @classmethod
    def from_config(cls, config: dict) -> "SearchSettings":
        provider = str(
            config.get("provider") or os.getenv("SEARCH_PROVIDER") or "tavily"
        ).strip().lower()
        if provider not in {"tavily", "serper"}:
            raise ValueError("SEARCH_PROVIDER 仅支持 tavily 或 serper")
        default_base = {
            "tavily": "https://api.tavily.com",
            "serper": "https://google.serper.dev",
        }[provider]
        redis_password = quote_plus(os.getenv("REDIS_PASSWORD", ""))
        redis_host = os.getenv("REDIS_HOST", "redis").strip() or "redis"
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_db = int(os.getenv("REDIS_DB", "0"))
        return cls(
            enabled=bool(config.get("enabled", True)),
            provider=provider,
            api_key=os.getenv("SEARCH_API_KEY", "").strip(),
            api_base=(os.getenv("SEARCH_API_BASE") or default_base).strip().rstrip("/"),
            max_results=_bounded(config.get("max_results"), 5, 1, 10),
            timeout_seconds=_bounded(config.get("timeout_seconds"), 15, 5, 60),
            rate_limit_per_minute=_bounded(
                os.getenv("SEARCH_RATE_LIMIT_PER_MINUTE"), 5, 1, 100
            ),
            redis_url=(
                f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
                if redis_password
                else f"redis://{redis_host}:{redis_port}/{redis_db}"
            ),
        )
