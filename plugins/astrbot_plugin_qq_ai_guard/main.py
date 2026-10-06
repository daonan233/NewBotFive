"""AstrBot 入口：消息落库、去重、AI 限流和 Token 统计。"""

from __future__ import annotations

import time
import uuid

import astrbot.api.message_components as Comp
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, MessageChain, filter
from astrbot.api.provider import LLMResponse, ProviderRequest
from astrbot.api.star import Context, Star

from qq_ai_common.permissions import PermissionService

from .config import GuardSettings
from .service import GuardService
from .usage import extract_usage, response_model


class QQAIGuardPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig) -> None:
        super().__init__(context)
        self.settings = GuardSettings.from_config(config)
        self.service = GuardService(self.settings)
        self.permissions = PermissionService.from_env()
        self.ready = False

    @filter.on_astrbot_loaded()
    async def on_astrbot_loaded(self) -> None:
        if not self.settings.enabled:
            logger.info("QQ AI 稳定性守卫已禁用")
            return
        try:
            await self.service.start()
            self.ready = True
            logger.info("QQ AI 稳定性守卫初始化完成")
        except Exception:
            logger.exception("QQ AI 稳定性守卫初始化失败")

    @filter.on_using_llm_tool()
    async def log_tool_call(self, event: AstrMessageEvent, tool, tool_args) -> None:
        """只记录工具名和调用主体，不记录可能含隐私的完整参数。"""
        logger.info(
            "LLM Tool 调用 tool=%s user=%s group=%s",
            getattr(tool, "name", "unknown"),
            event.get_sender_id(),
            event.get_group_id() or "private",
        )

    @filter.on_llm_tool_respond()
    async def log_tool_result(
        self, event: AstrMessageEvent, tool, tool_args, tool_result
    ) -> None:
        logger.info(
            "LLM Tool 完成 tool=%s user=%s group=%s success=%s",
            getattr(tool, "name", "unknown"),
            event.get_sender_id(),
            event.get_group_id() or "private",
            tool_result is not None,
        )

    @staticmethod
    def _message_type(event: AstrMessageEvent) -> str:
        return "group" if event.get_group_id() else "private"

    @staticmethod
    def _group_name(event: AstrMessageEvent) -> str:
        group = getattr(event.message_obj, "group", None)
        return str(getattr(group, "group_name", "") or getattr(group, "name", ""))

    @filter.event_message_type(filter.EventMessageType.ALL, priority=10000)
    async def capture_message(self, event: AstrMessageEvent) -> None:
        """保存所有消息；非唤醒群消息只归档，不触发默认 LLM。"""
        group_id = str(event.get_group_id() or "")
        if group_id and not event.is_at_or_wake_command:
            event.should_call_llm(False)

        if not self.ready:
            return
        sender_id = str(event.get_sender_id() or "")
        if not sender_id or sender_id == str(event.get_self_id() or ""):
            return
        message_id = str(getattr(event.message_obj, "message_id", "") or "").strip()
        if not message_id:
            logger.debug("消息缺少 message_id，跳过去重和落库")
            return

        identity = (
            f"{event.get_platform_id()}:{self._message_type(event)}:{message_id}"
        )
        try:
            if not await self.service.claim_message(identity):
                logger.info(
                    "拦截重复消息 platform=%s user=%s group=%s message_id=%s",
                    event.get_platform_id(),
                    sender_id,
                    group_id or "-",
                    message_id,
                )
                event.stop_event()
                return
            if self.settings.store_messages:
                content = event.get_message_outline()[: self.settings.message_max_chars]
                await self.service.repository.record_incoming_message(
                    message_id=message_id,
                    user_id=sender_id,
                    nickname=event.get_sender_name(),
                    group_id=group_id or None,
                    group_name=self._group_name(event),
                    message_type=self._message_type(event),
                    content=content,
                    platform=event.get_platform_name(),
                    unified_msg_origin=event.unified_msg_origin,
                    timestamp=getattr(event.message_obj, "timestamp", None),
                )
        except Exception:
            # 守卫故障必须降级，不能让正常聊天不可用。
            logger.exception(
                "消息守卫处理失败 user=%s group=%s message_id=%s",
                sender_id,
                group_id or "-",
                message_id,
            )

    @filter.on_waiting_llm_request(priority=10000)
    async def enforce_ai_rate_limit(self, event: AstrMessageEvent) -> None:
        """在获取会话锁之前限流，避免浪费模型请求。"""
        if not self.ready or self.permissions.is_super_admin(event):
            return
        user_id = str(event.get_sender_id() or "")
        if not user_id:
            return
        try:
            allowed, remaining = await self.service.consume_ai_quota(user_id)
        except Exception:
            logger.exception("AI 限流检查失败，已降级放行 user=%s", user_id)
            return
        if allowed:
            event.set_extra("qqai_rate_remaining", remaining)
            return
        await event.send(
            MessageChain(
                [
                    Comp.Plain(
                        f"请求有点快啦，请稍等一分钟再试～每分钟最多 "
                        f"{self.settings.ai_rate_limit_per_minute} 次 AI 对话。"
                    )
                ]
            )
        )
        event.stop_event()

    @filter.on_llm_request(priority=-10000)
    async def remember_request(
        self, event: AstrMessageEvent, request: ProviderRequest
    ) -> None:
        event.set_extra("qqai_request_model", str(request.model or ""))
        event.set_extra("qqai_request_prompt", str(request.prompt or ""))
        event.set_extra("qqai_request_started", time.monotonic())

    @filter.on_llm_response(priority=-10000)
    async def record_llm_usage(
        self, event: AstrMessageEvent, response: LLMResponse
    ) -> None:
        if not self.ready or response.role == "err":
            return
        try:
            usage = extract_usage(response)
            model = response_model(
                response, str(event.get_extra("qqai_request_model", ""))
            )
            request_id = str(getattr(response, "id", "") or uuid.uuid4())
            group_id = str(event.get_group_id() or "") or None
            await self.service.repository.record_llm_exchange(
                request_id=request_id,
                user_id=str(event.get_sender_id() or "unknown"),
                group_id=group_id,
                session_key=event.unified_msg_origin,
                prompt=str(event.get_extra("qqai_request_prompt", ""))[
                    : self.settings.message_max_chars
                ],
                response=str(response.completion_text or "")[
                    : self.settings.message_max_chars
                ],
                model=model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                message_type=self._message_type(event),
            )
            elapsed = time.monotonic() - float(
                event.get_extra("qqai_request_started", time.monotonic())
            )
            logger.info(
                "LLM 调用完成 user=%s group=%s model=%s tokens=%s elapsed=%.2fs",
                event.get_sender_id(),
                event.get_group_id() or "-",
                model,
                usage.total_tokens,
                elapsed,
            )
        except Exception:
            logger.exception("LLM 用量记录失败 user=%s", event.get_sender_id())

    @filter.command("usage", alias={"用量"})
    async def usage(self, event: AstrMessageEvent, scope: str = "me"):
        """查看今日个人用量；管理员可用 /usage today 查看全局。"""
        if not self.ready:
            yield event.plain_result("用量统计服务尚未就绪，请稍后重试。")
            return
        try:
            global_scope = scope.lower() in {"today", "all", "全局", "今日"}
            if global_scope:
                self.permissions.require_admin(event)
                summary = await self.service.usage_today()
                title = "今日全局 AI 用量"
            else:
                summary = await self.service.usage_today(str(event.get_sender_id()))
                title = "你今天的 AI 用量"
            yield event.plain_result(
                f"📊 {title}\n"
                f"请求次数：{summary.requests}\n"
                f"输入 Token：{summary.prompt_tokens}\n"
                f"输出 Token：{summary.completion_tokens}\n"
                f"合计 Token：{summary.total_tokens}"
            )
        except (PermissionError, ValueError) as exc:
            yield event.plain_result(str(exc))
        except Exception:
            logger.exception("查询用量失败 user=%s", event.get_sender_id())
            yield event.plain_result("查询用量失败，请稍后重试。")

    @filter.command("qqai_guard_status")
    async def guard_status(self, event: AstrMessageEvent):
        """管理员查看消息守卫运行状态。"""
        try:
            self.permissions.require_admin(event)
            if not self.ready:
                yield event.plain_result("QQ AI 稳定性守卫尚未就绪。")
                return
            postgres, redis = await self.service.health()
            yield event.plain_result(
                "QQ AI 稳定性守卫：运行中\n"
                f"PostgreSQL：{'正常' if postgres else '异常'}\n"
                f"Redis：{'正常' if redis else '异常'}\n"
                f"AI 限流：{self.settings.ai_rate_limit_per_minute} 次/分钟\n"
                f"消息去重：{'开启' if self.settings.deduplicate_messages else '关闭'}\n"
                f"消息落库：{'开启' if self.settings.store_messages else '关闭'}"
            )
        except PermissionError as exc:
            yield event.plain_result(str(exc))

    async def terminate(self) -> None:
        await self.service.close()
