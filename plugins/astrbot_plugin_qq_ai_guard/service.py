"""Phase 2 稳定性守卫业务服务。"""

from __future__ import annotations

import asyncio

from .cache import GuardCache
from .config import ConnectionSettings, GuardSettings
from .repository import GuardRepository, UsageSummary


class GuardService:
    def __init__(self, settings: GuardSettings) -> None:
        self.settings = settings
        self.cache = GuardCache()
        self.repository = GuardRepository()

    async def start(self) -> None:
        connections = ConnectionSettings.from_env()
        await asyncio.gather(
            self.cache.connect(connections.redis_url),
            self.repository.connect(connections.postgres_dsn),
        )

    async def close(self) -> None:
        await asyncio.gather(self.cache.close(), self.repository.close())

    async def health(self) -> tuple[bool, bool]:
        results = await asyncio.gather(
            self.repository.ping(), self.cache.ping(), return_exceptions=True
        )
        return results[0] is True, results[1] is True

    async def claim_message(self, identity: str) -> bool:
        if not self.settings.deduplicate_messages:
            return True
        return await self.cache.claim_message(identity, self.settings.dedup_ttl_seconds)

    async def consume_ai_quota(self, user_id: str) -> tuple[bool, int]:
        return await self.cache.consume_rate_limit(
            user_id, self.settings.ai_rate_limit_per_minute
        )

    async def usage_today(self, user_id: str | None = None) -> UsageSummary:
        return await self.repository.usage_today(
            timezone=self.settings.timezone, user_id=user_id
        )

