"""AstrBot 入口：命令、LLM Tool 与后台提醒投递。"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime
from zoneinfo import ZoneInfo

import astrbot.api.message_components as Comp
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, MessageChain, filter
from astrbot.api.star import Context, Star
from astrbot.core.star.filter.command import GreedyStr

from .config import ReminderSettings
from .parser import ParsedReminder, parse_reminder
from .repository import Reminder, ReminderRepository


class QQAIReminderPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig) -> None:
        super().__init__(context)
        self.settings = ReminderSettings.from_config(config)
        self.repository = ReminderRepository()
        self.ready = False
        self._stop = asyncio.Event()
        self._worker: asyncio.Task | None = None

    @filter.on_astrbot_loaded()
    async def on_astrbot_loaded(self) -> None:
        if not self.settings.enabled:
            logger.info("QQ AI 提醒插件已禁用")
            return
        try:
            await self.repository.connect(self.settings.postgres_dsn)
            await self.repository.recover_interrupted(self.settings.max_attempts)
            self.ready = True
            self._worker = asyncio.create_task(
                self._run_worker(), name="qq-ai-reminder-worker"
            )
            logger.info("QQ AI 持久化提醒初始化完成")
        except Exception:
            logger.exception("QQ AI 持久化提醒初始化失败")

    async def _create(self, event: AstrMessageEvent, parsed: ParsedReminder) -> int:
        if not self.ready:
            raise RuntimeError("提醒服务尚未就绪，请稍后重试。")
        return await self.repository.create(
            user_id=str(event.get_sender_id()),
            group_id=str(event.get_group_id() or ""),
            unified_msg_origin=event.unified_msg_origin,
            content=parsed.content,
            trigger_time=parsed.trigger_time,
        )

    def _format_time(self, value: datetime) -> str:
        return value.astimezone(ZoneInfo(self.settings.timezone)).strftime("%Y-%m-%d %H:%M")

    @filter.command("remind", alias={"提醒"})
    async def remind(self, event: AstrMessageEvent, args: GreedyStr = ""):
        """创建、查看或取消持久化提醒。"""
        value = str(args).strip()
        try:
            if value.lower() in {"list", "列表"}:
                items = await self.repository.list_pending(
                    str(event.get_sender_id()), event.unified_msg_origin
                )
                if not items:
                    yield event.plain_result("当前会话没有待执行提醒。")
                    return
                lines = [
                    f"#{item.id}  {self._format_time(item.trigger_time)}  {item.content}"
                    for item in items
                ]
                yield event.plain_result("⏰ 待执行提醒\n" + "\n".join(lines))
                return
            if value.lower().startswith(("cancel ", "取消 ")):
                raw_id = value.split(maxsplit=1)[1]
                if not raw_id.isdigit():
                    raise ValueError("提醒编号必须是数字。")
                cancelled = await self.repository.cancel(
                    int(raw_id), str(event.get_sender_id()), event.unified_msg_origin
                )
                if not cancelled:
                    raise ValueError("没有找到可取消的待执行提醒。")
                yield event.plain_result(f"已取消提醒 #{raw_id}。")
                return
            parsed = parse_reminder(value, self.settings.timezone)
            reminder_id = await self._create(event, parsed)
            yield event.plain_result(
                f"⏰ 提醒 #{reminder_id} 已创建\n"
                f"时间：{self._format_time(parsed.trigger_time)}\n内容：{parsed.content}"
            )
        except (ValueError, RuntimeError) as exc:
            yield event.plain_result(str(exc))
        except Exception:
            logger.exception("提醒操作失败 user=%s", event.get_sender_id())
            yield event.plain_result("提醒操作失败，请稍后重试。")

    @filter.llm_tool(name="create_reminder")
    async def create_reminder(
        self, event: AstrMessageEvent, time: str, content: str
    ) -> str:
        """为当前用户创建提醒。当用户明确要求未来提醒时使用。

        Args:
            time(string): 提醒时间，例如“10分钟后”“明天 09:00”或“2026-10-10 15:00”。
            content(string): 到期时要提醒用户的内容。
        """
        try:
            parsed = parse_reminder(f"{time.strip()} {content.strip()}", self.settings.timezone)
            reminder_id = await self._create(event, parsed)
            return (
                f"提醒 #{reminder_id} 已创建，将在 "
                f"{self._format_time(parsed.trigger_time)} 提醒：{parsed.content}"
            )
        except (ValueError, RuntimeError) as exc:
            return str(exc)

    async def _run_worker(self) -> None:
        while not self._stop.is_set():
            try:
                due = await self.repository.claim_due(self.settings.batch_size)
                for reminder in due:
                    await self._deliver(reminder)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("扫描到期提醒失败")
            try:
                await asyncio.wait_for(
                    self._stop.wait(), timeout=self.settings.poll_interval_seconds
                )
            except TimeoutError:
                pass

    async def _deliver(self, reminder: Reminder) -> None:
        try:
            chain: list = []
            if reminder.group_id:
                chain.append(Comp.At(qq=reminder.user_id))
                chain.append(Comp.Plain(" "))
            chain.append(Comp.Plain(f"⏰ 提醒：{reminder.content}"))
            await self.context.send_message(
                reminder.unified_msg_origin, MessageChain(chain)
            )
            await self.repository.mark_sent(reminder.id)
        except Exception as exc:
            logger.exception("发送提醒失败 reminder_id=%s", reminder.id)
            await self.repository.mark_failed_or_retry(
                reminder.id, reminder.attempts, self.settings.max_attempts, str(exc)
            )

    async def terminate(self) -> None:
        self.ready = False
        self._stop.set()
        if self._worker is not None:
            self._worker.cancel()
            with suppress(asyncio.CancelledError):
                await self._worker
        await self.repository.close()
