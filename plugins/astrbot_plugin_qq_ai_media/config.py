"""图片能力配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote_plus


def _int(value: object, default: int, low: int, high: int) -> int:
    try:
        parsed = int(default if value in (None, "") else value)
    except (TypeError, ValueError):
        parsed = default
    return max(low, min(high, parsed))


@dataclass(frozen=True, slots=True)
class MediaSettings:
    enabled: bool
    vision_model: str
    image_model: str
    image_api_base: str
    image_api_key: str
    timeout_seconds: int
    image_rate_limit: int
    redis_url: str
    output_dir: str
    local_random_enabled: bool
    local_random_dir: str
    local_random_recursive: bool

    @classmethod
    def from_config(cls, config: dict) -> "MediaSettings":
        password = quote_plus(os.getenv("REDIS_PASSWORD", ""))
        host = os.getenv("REDIS_HOST", "redis")
        port = int(os.getenv("REDIS_PORT", "6379"))
        db = int(os.getenv("REDIS_DB", "0"))
        return cls(
            enabled=bool(config.get("enabled", True)),
            vision_model=str(config.get("vision_model") or os.getenv("VISION_MODEL", "")).strip(),
            image_model=str(config.get("image_model") or os.getenv("IMAGE_MODEL", "")).strip(),
            image_api_base=os.getenv("IMAGE_API_BASE", "").strip().rstrip("/"),
            image_api_key=os.getenv("IMAGE_API_KEY", "").strip(),
            timeout_seconds=_int(config.get("timeout_seconds"), 90, 15, 180),
            image_rate_limit=_int(os.getenv("IMAGE_RATE_LIMIT_PER_MINUTE"), 2, 1, 30),
            redis_url=(
                f"redis://:{password}@{host}:{port}/{db}"
                if password
                else f"redis://{host}:{port}/{db}"
            ),
            output_dir=os.getenv("IMAGE_OUTPUT_DIR", "/AstrBot/data/qq_ai_generated"),
            local_random_enabled=bool(config.get("local_random_enabled", True)),
            local_random_dir=str(
                config.get("local_random_dir")
                or os.getenv(
                    "RANDOM_IMAGE_CONTAINER_DIR",
                    "/AstrBot/data/qq_ai_random_images",
                )
            ).strip(),
            local_random_recursive=bool(config.get("local_random_recursive", True)),
        )
