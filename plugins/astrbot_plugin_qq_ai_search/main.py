"""AstrBot 入口：联网搜索命令及 LLM Tool。"""

from __future__ import annotations

import httpx
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star
from astrbot.core.star.filter.command import GreedyStr

from qq_ai_common.permissions import PermissionService

from .config import SearchSettings
from .providers import SearchResult
from .service import SearchService


class QQAISearchPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig) -> None:
        super().__init__(context)
        self.settings = SearchSettings.from_config(config)
        self.service = SearchService(self.settings)
        self.permissions = PermissionService.from_env()
        self.ready = False

    @filter.on_astrbot_loaded()
    async def on_astrbot_loaded(self) -> None:
        if not self.settings.enabled:
            logger.info("QQ AI 联网搜索已禁用")
            return
        try:
            await self.service.start()
            self.ready = True
            if self.settings.api_key:
                logger.info("QQ AI 联网搜索初始化完成 provider=%s", self.settings.provider)
            else:
                logger.warning("QQ AI 联网搜索已加载，但尚未配置 SEARCH_API_KEY")
        except Exception:
            logger.exception("QQ AI 联网搜索初始化失败")

    async def _search(self, event: AstrMessageEvent, query: str) -> tuple[SearchResult, ...]:
        if not self.ready:
            raise RuntimeError("联网搜索服务尚未就绪，请稍后重试。")
        user_id = str(event.get_sender_id() or "anonymous")
        if self.permissions.is_super_admin(event):
            user_id = f"admin:{user_id}:{event.get_message_id()}"
        return await self.service.search(user_id, query)

    @staticmethod
    def _render(results: tuple[SearchResult, ...]) -> str:
        if not results:
            return "没有找到相关搜索结果。"
        sections = []
        for index, item in enumerate(results, 1):
            snippet = item.snippet.replace("\n", " ").strip()
            if len(snippet) > 240:
                snippet = snippet[:237] + "..."
            sections.append(f"{index}. {item.title}\n{snippet}\n{item.url}")
        return "🔎 搜索结果\n\n" + "\n\n".join(sections)

    @filter.command("search", alias={"搜索"})
    async def search_command(self, event: AstrMessageEvent, query: GreedyStr):
        """搜索互联网并返回带来源链接的结果。"""
        try:
            results = await self._search(event, str(query))
            yield event.plain_result(self._render(results))
        except (ValueError, RuntimeError) as exc:
            yield event.plain_result(str(exc))
        except httpx.HTTPStatusError as exc:
            logger.warning("搜索 API 返回错误 status=%s", exc.response.status_code)
            yield event.plain_result("搜索服务返回错误，请检查 API Key 或稍后重试。")
        except httpx.HTTPError:
            logger.exception("搜索网络请求失败")
            yield event.plain_result("暂时无法连接搜索服务，请稍后重试。")
        except Exception:
            logger.exception("搜索失败")
            yield event.plain_result("搜索失败，请稍后重试。")

    @filter.llm_tool(name="web_search")
    async def web_search(self, event: AstrMessageEvent, query: str) -> str:
        """搜索互联网获取最新或需要核实的信息，并返回可引用的网页来源。

        Args:
            query(string): 简洁、具体的搜索关键词或问题。
        """
        try:
            return self._render(await self._search(event, query))
        except (ValueError, RuntimeError) as exc:
            return str(exc)
        except httpx.HTTPError as exc:
            logger.warning("LLM 搜索工具请求失败: %s", type(exc).__name__)
            return "联网搜索暂时不可用，请稍后重试。"

    async def terminate(self) -> None:
        self.ready = False
        await self.service.close()

