"""AstrBot 入口：显式长期记忆及上下文注入。"""

from __future__ import annotations

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.provider import ProviderRequest
from astrbot.api.star import Context, Star
from astrbot.core.star.filter.command import GreedyStr

from .config import MemorySettings
from .prompt import memory_context
from .repository import MemoryRepository


class QQAIMemoryPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig) -> None:
        super().__init__(context)
        self.settings = MemorySettings.from_config(config)
        self.repository = MemoryRepository()
        self.ready = False

    @filter.on_astrbot_loaded()
    async def on_astrbot_loaded(self) -> None:
        if not self.settings.enabled:
            logger.info("QQ AI 长期记忆已禁用")
            return
        try:
            await self.repository.connect(self.settings.postgres_dsn)
            self.ready = True
            logger.info("QQ AI 长期记忆初始化完成")
        except Exception:
            logger.exception("QQ AI 长期记忆初始化失败")

    @staticmethod
    def _scope(event: AstrMessageEvent) -> tuple[str, str | None]:
        return str(event.get_sender_id()), str(event.get_group_id()) if event.get_group_id() else None

    @filter.command("remember", alias={"记住"})
    async def remember(self, event: AstrMessageEvent, content: GreedyStr):
        """在当前私聊或群聊范围保存一条长期记忆。"""
        value = str(content).strip()
        if not self.ready:
            yield event.plain_result("长期记忆服务尚未就绪，请稍后重试。")
            return
        if not value or len(value) > 500:
            yield event.plain_result("记忆内容必须为 1～500 个字符。")
            return
        try:
            user_id, group_id = self._scope(event)
            memory_id = await self.repository.add(
                user_id, group_id, value, self.settings.max_memories_per_scope
            )
            yield event.plain_result(f"已记住，编号 #{memory_id}。")
        except (ValueError, RuntimeError) as exc:
            yield event.plain_result(str(exc))
        except Exception:
            logger.exception("保存长期记忆失败 user=%s", event.get_sender_id())
            yield event.plain_result("保存失败，请稍后重试。")

    @filter.command("memory", alias={"记忆"})
    async def memory(self, event: AstrMessageEvent):
        """查看当前私聊或群聊范围内自己的记忆。"""
        try:
            items = await self.repository.list_scope(*self._scope(event))
            if not items:
                yield event.plain_result("当前范围还没有保存长期记忆。")
                return
            lines = [f"#{item.id}  {item.content}" for item in items]
            yield event.plain_result("🧠 长期记忆\n" + "\n".join(lines))
        except Exception:
            logger.exception("读取长期记忆失败")
            yield event.plain_result("读取失败，请稍后重试。")

    @filter.command("forget", alias={"忘记"})
    async def forget(self, event: AstrMessageEvent, memory_id: int):
        """删除自己在当前范围内保存的指定记忆。"""
        try:
            deleted = await self.repository.forget(memory_id, *self._scope(event))
            if not deleted:
                yield event.plain_result("没有找到属于你的这条记忆。")
                return
            yield event.plain_result(f"已删除记忆 #{memory_id}。")
        except Exception:
            logger.exception("删除长期记忆失败")
            yield event.plain_result("删除失败，请稍后重试。")

    @filter.on_llm_request(priority=500)
    async def inject_memories(
        self, event: AstrMessageEvent, request: ProviderRequest
    ) -> None:
        if not self.ready:
            return
        try:
            items = await self.repository.relevant(
                *self._scope(event), self.settings.inject_limit
            )
            context = memory_context(item.content for item in items)
            if context:
                request.system_prompt = (request.system_prompt or "") + context
        except Exception:
            logger.exception("长期记忆注入失败，已降级为无记忆对话")

    async def terminate(self) -> None:
        self.ready = False
        await self.repository.close()

