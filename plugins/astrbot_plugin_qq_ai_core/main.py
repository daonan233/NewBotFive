"""AstrBot Star 入口，只放事件处理；业务逻辑位于 service.py。"""

from __future__ import annotations

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star

from .service import InfrastructureService


class QQAICorePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig) -> None:
        super().__init__(context)
        self.config = config
        timeout = max(1, int(config.get("connect_timeout_seconds", 5)))
        self.infrastructure = InfrastructureService(timeout=float(timeout))

    @filter.on_astrbot_loaded()
    async def on_astrbot_loaded(self) -> None:
        """AstrBot 初始化完成后建立连接池。"""
        if not bool(self.config.get("enabled", True)):
            logger.info("QQ AI Core 已由插件配置禁用")
            return
        try:
            await self.infrastructure.start()
        except Exception as exc:
            # 基础设施暂时不可用时保留 AstrBot 主流程，方便从 WebUI 排障。
            logger.error("QQ AI Core 初始化失败：%s", type(exc).__name__)

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("qqai_status")
    async def qqai_status(self, event: AstrMessageEvent):
        """管理员查看 PostgreSQL 与 Redis 健康状态。"""
        if not bool(self.config.get("enabled", True)):
            yield event.plain_result("QQ AI 基础设施插件已禁用。")
            return

        status = await self.infrastructure.health()
        postgres = "正常" if status.postgres else "异常"
        redis = "正常" if status.redis else "异常"
        overall = "正常" if status.healthy else "降级"
        yield event.plain_result(
            f"QQ AI 基础设施：{overall}\nPostgreSQL：{postgres}\nRedis：{redis}"
        )

    async def terminate(self) -> None:
        """插件卸载或禁用时释放连接池。"""
        await self.infrastructure.close()

