"""基础设施生命周期与健康状态。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from astrbot.api import logger

from .cache import Cache
from .config import InfrastructureSettings
from .database import Database


@dataclass(frozen=True, slots=True)
class HealthStatus:
    postgres: bool
    redis: bool

    @property
    def healthy(self) -> bool:
        return self.postgres and self.redis


class InfrastructureService:
    def __init__(self, timeout: float) -> None:
        self.timeout = timeout
        self.database = Database()
        self.cache = Cache()

    async def start(self) -> None:
        settings = InfrastructureSettings.from_env()
        results = await asyncio.gather(
            self.database.connect(
                settings.postgres_dsn,
                settings.postgres_pool_min_size,
                settings.postgres_pool_max_size,
                self.timeout,
            ),
            self.cache.connect(
                settings.redis_url,
                settings.redis_pool_max_connections,
                self.timeout,
            ),
            return_exceptions=True,
        )
        for component, result in zip(("PostgreSQL", "Redis"), results, strict=True):
            if isinstance(result, Exception):
                logger.error("%s 初始化失败：%s", component, type(result).__name__)
            else:
                logger.info("QQ AI Core: %s 连接池初始化完成", component)

    async def health(self) -> HealthStatus:
        async def safe_ping(name: str, operation) -> bool:
            try:
                return bool(await asyncio.wait_for(operation(), timeout=self.timeout))
            except Exception as exc:  # 健康检查必须降级，不能中断 AstrBot。
                logger.warning("%s 健康检查失败：%s", name, type(exc).__name__)
                return False

        postgres, redis = await asyncio.gather(
            safe_ping("PostgreSQL", self.database.ping),
            safe_ping("Redis", self.cache.ping),
        )
        return HealthStatus(postgres=postgres, redis=redis)

    async def close(self) -> None:
        await asyncio.gather(self.database.close(), self.cache.close())

