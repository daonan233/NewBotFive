"""AstrBot 入口：群总结、群统计与群友语录。"""

from __future__ import annotations

from datetime import datetime, timezone

import astrbot.api.message_components as Comp
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star

from qq_ai_common.permissions import PermissionService

from .config import GroupSettings
from .repository import GroupRepository
from .text_stats import top_keywords


class QQAIGroupPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig) -> None:
        super().__init__(context)
        self.settings = GroupSettings.from_config(config)
        self.repository = GroupRepository()
        self.permissions = PermissionService.from_env()
        self.ready = False

    @filter.on_astrbot_loaded()
    async def on_astrbot_loaded(self) -> None:
        if not self.settings.enabled:
            logger.info("QQ AI 群聊助手已禁用")
            return
        try:
            await self.repository.connect(self.settings.postgres_dsn)
            self.ready = True
            logger.info("QQ AI 群聊助手初始化完成")
        except Exception:
            logger.exception("QQ AI 群聊助手初始化失败")

    @staticmethod
    def _group(event: AstrMessageEvent) -> str:
        group_id = str(event.get_group_id() or "")
        if not group_id:
            raise ValueError("这个命令只能在群聊中使用。")
        return group_id

    @filter.command("summary", alias={"总结"})
    async def summary(self, event: AstrMessageEvent, count: int = 0):
        """总结当前群最近若干条消息。"""
        if not self.ready:
            yield event.plain_result("群总结服务尚未就绪，请稍后重试。")
            return
        try:
            group_id = self._group(event)
            count = count or self.settings.summary_default_messages
            if count < 10 or count > self.settings.summary_max_messages:
                raise ValueError(
                    f"总结条数必须在 10 到 {self.settings.summary_max_messages} 之间。"
                )
            messages = await self.repository.recent_messages(group_id, count)
            if len(messages) < 2:
                raise ValueError("可用于总结的群消息还不够，请先聊一会儿。")
            transcript = "\n".join(
                f"[{item.created_at:%m-%d %H:%M}] {item.nickname}: {item.content}"
                for item in messages
            )
            prompt = (
                "请总结下面的 QQ 群聊天记录。不要添加记录中不存在的信息，也不要输出推理过程。\n"
                "固定使用以下结构：\n"
                "【讨论主题】\n【重要信息】\n【决定与结论】\n【待办事项】\n【有趣内容】\n\n"
                f"聊天记录：\n{transcript}"
            )
            yield event.request_llm(
                prompt=prompt,
                contexts=[],
                system_prompt=(
                    "你是严谨的群聊记录整理助手。只依据给定记录总结，保护隐私，"
                    "内容不足的栏目写“暂无”。"
                ),
            )
        except (ValueError, RuntimeError) as exc:
            yield event.plain_result(str(exc))
        except Exception:
            logger.exception("群总结失败 group=%s", event.get_group_id())
            yield event.plain_result("群总结失败，请稍后重试。")

    @filter.command("stats", alias={"群统计"})
    async def stats(self, event: AstrMessageEvent, period: str = "today"):
        """统计今日、本周或本月群聊活跃情况。"""
        if not self.ready:
            yield event.plain_result("群统计服务尚未就绪，请稍后重试。")
            return
        aliases = {"今日": "today", "今天": "today", "本周": "week", "本月": "month"}
        period = aliases.get(period.lower(), period.lower())
        if period not in {"today", "week", "month"}:
            yield event.plain_result("用法：/stats [today|week|month]")
            return
        try:
            result = await self.repository.stats(
                self._group(event), period, self.settings.timezone
            )
            labels = {"today": "今日", "week": "本周", "month": "本月"}
            top_users = "\n".join(
                f"{index}. {item.nickname}：{item.messages} 条"
                for index, item in enumerate(result.top_users, 1)
            ) or "暂无"
            keywords = "、".join(top_keywords(list(result.contents))) or "暂无"
            active_hour = (
                f"{result.active_hour:02d}:00–{(result.active_hour + 1) % 24:02d}:00"
                if result.active_hour is not None
                else "暂无"
            )
            yield event.plain_result(
                f"📈 {labels[period]}群聊统计\n"
                f"消息数量：{result.messages}\n"
                f"活跃人数：{result.active_users}\n"
                f"活跃时段：{active_hour}\n"
                f"热门关键词：{keywords}\n"
                f"活跃用户：\n{top_users}"
            )
        except Exception:
            logger.exception("群统计失败 group=%s", event.get_group_id())
            yield event.plain_result("群统计失败，请稍后重试。")

    @filter.command("quote", alias={"语录"})
    async def quote(self, event: AstrMessageEvent, action: str = "random"):
        """回复消息使用 /quote add 收录；/quote 随机查看。"""
        if not self.ready:
            yield event.plain_result("群友语录服务尚未就绪，请稍后重试。")
            return
        try:
            group_id = self._group(event)
            action = action.lower()
            if action in {"add", "添加", "收录"}:
                if self.settings.quote_admin_only_add:
                    self.permissions.require_admin(event)
                reply = next(
                    (item for item in event.get_messages() if isinstance(item, Comp.Reply)),
                    None,
                )
                if reply is None:
                    raise ValueError("请回复一条文字消息后发送 /quote add。")
                content = str(reply.message_str or "").strip()
                if not content:
                    raise ValueError("被回复的消息没有可收录的文字内容。")
                if len(content) > 1000:
                    raise ValueError("语录内容不能超过 1000 个字符。")
                quoted_at = (
                    datetime.fromtimestamp(int(reply.time), tz=timezone.utc)
                    if reply.time
                    else None
                )
                quote_id = await self.repository.add_quote(
                    source_message_id=str(reply.id),
                    user_id=str(reply.sender_id or "unknown"),
                    nickname=str(reply.sender_nickname or reply.sender_id or "未知用户"),
                    group_id=group_id,
                    content=content,
                    quoted_at=quoted_at,
                    created_by=str(event.get_sender_id()),
                )
                yield event.plain_result(f"语录已收录，编号 #{quote_id}。")
                return
            if action not in {"random", "随机", ""}:
                yield event.plain_result("用法：回复消息后 /quote add；随机查看使用 /quote")
                return
            target = next(
                (
                    str(item.qq)
                    for item in event.get_messages()
                    if isinstance(item, Comp.At) and str(item.qq) != str(event.get_self_id())
                ),
                None,
            )
            item = await self.repository.random_quote(group_id, target)
            if item is None:
                raise ValueError("暂时没有符合条件的群友语录。")
            yield event.plain_result(
                f"💬 群友语录 #{item.id}\n{item.nickname}：{item.content}"
            )
        except (ValueError, PermissionError) as exc:
            yield event.plain_result(str(exc))
        except Exception:
            logger.exception("群友语录操作失败 group=%s", event.get_group_id())
            yield event.plain_result("群友语录操作失败，请稍后重试。")

    async def terminate(self) -> None:
        await self.repository.close()

