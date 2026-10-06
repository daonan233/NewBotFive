"""AstrBot 入口：思考模式路由与群抽奖小游戏。"""

from __future__ import annotations

import secrets

import astrbot.api.message_components as Comp
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.provider import ProviderRequest
from astrbot.api.star import Context, Star
from astrbot.core.star.filter.command import GreedyStr
from qq_ai_common.permissions import PermissionService

from .commands import HELP_TEXT, parse_choices, parse_lottery_command, validate_dice_sides
from .config import FunSettings
from .service import FunService
from .routing import route_kind


class QQAIThinkAndFunPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig) -> None:
        super().__init__(context)
        self.settings = FunSettings.from_config(config)
        self.service = FunService(self.settings)
        self.permissions = PermissionService.from_env()
        self.ready = False

    @staticmethod
    def _scope(event: AstrMessageEvent) -> str:
        return f"{event.unified_msg_origin}:{event.get_sender_id()}"

    @staticmethod
    def _require_group(event: AstrMessageEvent) -> str:
        group_id = event.get_group_id()
        if not group_id:
            raise ValueError("这个命令只能在群聊中使用。")
        return str(group_id)

    @filter.on_astrbot_loaded()
    async def on_astrbot_loaded(self) -> None:
        if not self.settings.enabled:
            logger.info("QQ AI 思考与抽奖插件已禁用")
            return
        try:
            await self.service.start()
            self.ready = True
            logger.info("QQ AI 思考与抽奖插件初始化完成")
        except Exception:
            logger.exception("QQ AI 思考与抽奖插件初始化失败")

    @filter.command("think", alias={"思考"})
    async def think(self, event: AstrMessageEvent, mode: str = "status"):
        """查看或切换当前用户在当前会话的推理模型。"""
        if not self.ready:
            yield event.plain_result("思考模式服务尚未就绪，请稍后重试。")
            return
        aliases = {"开": "on", "开启": "on", "关": "off", "关闭": "off", "默认": "auto"}
        mode = aliases.get(mode.lower(), mode.lower())
        scope = self._scope(event)
        if mode in {"status", "状态"}:
            current = await self.service.think_mode(scope)
        elif mode in {"on", "off"}:
            await self.service.think_modes.set(scope, mode)
            current = mode
        elif mode == "auto":
            await self.service.think_modes.clear(scope)
            current = self.settings.default_think_mode
        else:
            yield event.plain_result("用法：/think [on|off|auto]（也支持 开/关/默认）")
            return

        model = self.service.model_for_mode(current)
        state = "开启" if current == "on" else "关闭"
        if not model:
            yield event.plain_result(
                f"当前思考模式：{state}。但对应模型尚未在插件配置或环境变量中设置。"
            )
        else:
            yield event.plain_result(f"当前思考模式：{state}\n本轮路由模型：{model}")

    @filter.on_llm_request()
    async def route_thinking_model(
        self, event: AstrMessageEvent, request: ProviderRequest
    ) -> None:
        """只使用当前公开的 model 字段，不修改 Provider 私有实现。"""
        if not self.ready:
            return
        # 图片请求交给媒体插件选择 VISION_MODEL，避免思考模式覆盖图片路由。
        if request.image_urls:
            return
        explicit_mode = await self.service.think_modes.get_optional(self._scope(event))
        if explicit_mode:
            model = self.service.model_for_mode(explicit_mode)
        else:
            kind = route_kind(str(request.prompt or ""))
            model = {
                "coding": self.settings.coding_model,
                "smart": self.settings.reasoning_model,
                "fast": self.settings.fast_model,
                "default": self.settings.normal_model,
            }[kind] or self.settings.normal_model
        if model:
            request.model = model

    @filter.command("lottery", alias={"抽奖"})
    async def lottery(self, event: AstrMessageEvent, args: GreedyStr):
        """群抽奖：发起、参加、查看、开奖或取消。"""
        if not self.ready:
            yield event.plain_result("抽奖服务尚未就绪，请稍后重试。")
            return
        try:
            group_id = self._require_group(event)
            command = parse_lottery_command(args, self.settings.lottery_max_winners)
            sender_id = str(event.get_sender_id())
            nickname = event.get_sender_name() or sender_id

            if command.action == "help":
                yield event.plain_result(HELP_TEXT)
                return
            if command.action == "start":
                if (
                    self.settings.lottery_admin_only_start
                    and not self.permissions.is_admin(event)
                ):
                    raise PermissionError("只有管理员可以发起抽奖。")
                lottery = await self.service.lotteries.create(
                    group_id,
                    event.unified_msg_origin,
                    command.prize,
                    command.winner_count,
                    sender_id,
                )
                yield event.plain_result(
                    f"🎉 抽奖已开始！\n奖品：{lottery.prize}\n"
                    f"中奖人数：{lottery.winner_count}\n发送 /lottery join 参加。"
                )
                return
            if command.action == "join":
                joined = await self.service.lotteries.join(
                    group_id, sender_id, nickname
                )
                text = "参加成功，祝你好运！" if joined else "你已经参加过本次抽奖了。"
                yield event.plain_result(text)
                return

            status = await self.service.lotteries.get_open(group_id)
            if status is None:
                raise ValueError("本群当前没有进行中的抽奖。")
            if command.action == "status":
                preview = "、".join(e.nickname or e.user_id for e in status.entries[:20])
                suffix = "……" if len(status.entries) > 20 else ""
                yield event.plain_result(
                    f"🎁 奖品：{status.lottery.prize}\n"
                    f"中奖人数：{status.lottery.winner_count}\n"
                    f"参与人数：{len(status.entries)}\n"
                    f"参与者：{preview or '暂无'}{suffix}"
                )
                return
            if (
                sender_id != status.lottery.created_by
                and not self.permissions.is_admin(event)
            ):
                raise PermissionError("只有抽奖创建者或管理员可以开奖/取消。")
            if command.action == "cancel":
                await self.service.lotteries.cancel(group_id)
                yield event.plain_result("本次抽奖已取消。")
                return
            if command.action == "draw":
                result = await self.service.lotteries.draw(group_id)
                winners = [entry for entry in result.entries if entry.won]
                chain: list = [Comp.Plain(f"🎊 开奖啦！奖品：{result.lottery.prize}\n中奖者：")]
                for index, winner in enumerate(winners):
                    if index:
                        chain.append(Comp.Plain("、"))
                    chain.append(Comp.At(qq=winner.user_id))
                yield event.chain_result(chain)
                return
        except (ValueError, PermissionError, RuntimeError) as exc:
            yield event.plain_result(str(exc))

    @filter.command("roll", alias={"骰子"})
    async def roll(self, event: AstrMessageEvent, sides: int = 6):
        """投掷指定面数的公平随机骰子。"""
        try:
            sides = validate_dice_sides(sides)
            value = secrets.randbelow(sides) + 1
            yield event.plain_result(f"🎲 d{sides} = {value}")
        except ValueError as exc:
            yield event.plain_result(str(exc))

    @filter.command("pick", alias={"选择"})
    async def pick(self, event: AstrMessageEvent, choices_text: GreedyStr):
        """从使用竖线分隔的多个选项中随机选择一个。"""
        try:
            choices = parse_choices(choices_text)
            yield event.plain_result(f"🎯 我选：{secrets.choice(choices)}")
        except ValueError as exc:
            yield event.plain_result(str(exc))

    async def terminate(self) -> None:
        await self.service.close()
