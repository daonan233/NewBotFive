"""思考路由和抽奖业务服务。"""

from __future__ import annotations

import asyncio

from .config import ConnectionSettings, FunSettings
from .repository import LotteryRepository
from .state import ThinkModeStore


class FunService:
    def __init__(self, settings: FunSettings) -> None:
        self.settings = settings
        self.lotteries = LotteryRepository()
        self.think_modes = ThinkModeStore()

    async def start(self) -> None:
        connections = ConnectionSettings.from_env()
        await asyncio.gather(
            self.lotteries.connect(connections.postgres_dsn),
            self.think_modes.connect(connections.redis_url),
        )

    async def close(self) -> None:
        await asyncio.gather(self.lotteries.close(), self.think_modes.close())

    async def think_mode(self, scope: str) -> str:
        return await self.think_modes.get(scope, self.settings.default_think_mode)

    def model_for_mode(self, mode: str) -> str:
        return (
            self.settings.reasoning_model
            if mode == "on"
            else self.settings.normal_model
        )

