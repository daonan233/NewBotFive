"""AstrBot 入口：计算器与实时天气 Agent Tools。"""

from __future__ import annotations

import httpx
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star
from astrbot.core.star.filter.command import GreedyStr

from .calculator import calculate
from .weather import WeatherService


class QQAIToolsPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig) -> None:
        super().__init__(context)
        self.enabled = bool(config.get("enabled", True))
        try:
            timeout = max(5, min(30, int(config.get("weather_timeout_seconds", 12))))
        except (TypeError, ValueError):
            timeout = 12
        self.weather = WeatherService(timeout)

    @filter.on_astrbot_loaded()
    async def loaded(self) -> None:
        logger.info("QQ AI 通用 Agent 工具%s", "初始化完成" if self.enabled else "已禁用")

    @filter.command("calc", alias={"计算"})
    async def calc_command(self, event: AstrMessageEvent, expression: GreedyStr):
        if not self.enabled:
            yield event.plain_result("通用工具插件已禁用。")
            return
        try:
            yield event.plain_result(f"🧮 {expression} = {calculate(str(expression))}")
        except ValueError as exc:
            yield event.plain_result(str(exc))

    @filter.llm_tool(name="calculator")
    async def calculator(self, event: AstrMessageEvent, expression: str) -> str:
        """安全计算数学表达式，适合需要精确算术时使用。

        Args:
            expression(string): 只含数字、算术运算符及 abs/round/sqrt/min/max 的表达式。
        """
        if not self.enabled:
            return "通用工具插件已禁用。"
        try:
            return str(calculate(expression))
        except ValueError as exc:
            return str(exc)

    @filter.command("weather", alias={"天气"})
    async def weather_command(self, event: AstrMessageEvent, location: GreedyStr):
        if not self.enabled:
            yield event.plain_result("通用工具插件已禁用。")
            return
        try:
            yield event.plain_result(await self.weather.current(str(location)))
        except ValueError as exc:
            yield event.plain_result(str(exc))
        except httpx.HTTPError:
            logger.exception("天气 API 请求失败")
            yield event.plain_result("天气服务暂时不可用，请稍后重试。")

    @filter.llm_tool(name="get_weather")
    async def get_weather(self, event: AstrMessageEvent, location: str) -> str:
        """查询指定城市或地区的实时天气与三日预报。

        Args:
            location(string): 城市、区县或“城市, 国家/省份”形式的地点。
        """
        if not self.enabled:
            return "通用工具插件已禁用。"
        try:
            return await self.weather.current(location)
        except ValueError as exc:
            return str(exc)
        except httpx.HTTPError:
            return "天气服务暂时不可用，请稍后重试。"

    async def terminate(self) -> None:
        await self.weather.close()
