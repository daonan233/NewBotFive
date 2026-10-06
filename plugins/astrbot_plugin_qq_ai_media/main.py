"""AstrBot 入口：图片理解与 AI 生图。"""

from __future__ import annotations

import asyncio

import httpx
import astrbot.api.message_components as Comp
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.provider import ProviderRequest
from astrbot.api.star import Context, Star
from astrbot.core.star.filter.command import GreedyStr

from qq_ai_common.permissions import PermissionService

from .config import MediaSettings
from .local_gallery import choose_local_image
from .service import ImageService


class QQAIMediaPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig) -> None:
        super().__init__(context)
        self.settings = MediaSettings.from_config(config)
        self.service = ImageService(self.settings)
        self.permissions = PermissionService.from_env()
        self.ready = False

    @filter.on_astrbot_loaded()
    async def on_astrbot_loaded(self) -> None:
        if not self.settings.enabled:
            logger.info("QQ AI 图片能力已禁用")
            return
        try:
            await self.service.start()
            self.ready = True
            if not self.settings.vision_model:
                logger.warning("未配置 VISION_MODEL，图片理解将使用 AstrBot 当前模型")
            if not self.settings.image_api_key:
                logger.warning("未配置 IMAGE_API_KEY，/draw 将返回配置提示")
            if self.settings.local_random_enabled:
                logger.info(
                    "本地随机图片已启用 directory=%s recursive=%s",
                    self.settings.local_random_dir,
                    self.settings.local_random_recursive,
                )
            logger.info("QQ AI 图片能力初始化完成")
        except Exception:
            logger.exception("QQ AI 图片能力初始化失败")

    @staticmethod
    def _images(event: AstrMessageEvent) -> list[str]:
        results: list[str] = []
        for item in event.get_messages():
            if not isinstance(item, Comp.Image):
                continue
            value = str(item.url or item.file or item.path or "").strip()
            if value:
                results.append(value)
        return results

    @filter.command("vision", alias={"看图"})
    async def vision(self, event: AstrMessageEvent, question: GreedyStr = "这张图片是什么？"):
        """分析同一条消息中的 QQ 图片。"""
        # 中文别名在 AstrBot 4.28 中可能不会被标记为 special 事件；显式终止
        # 后续流水线，避免命令执行后又进入普通 LLM 对话。
        event.stop_event()
        images = self._images(event)
        if not images:
            yield event.plain_result("请在发送 /vision 问题 时同时附带至少一张图片。")
            return
        prompt = str(question).strip() or "请描述图片并回答其中涉及的问题。"
        yield event.request_llm(
            prompt=prompt,
            image_urls=images[:4],
            contexts=[],
            system_prompt="你是图片理解助手。只描述图中可见内容，不确定时明确说明。",
        )

    @filter.on_llm_request(priority=1000)
    async def route_vision_model(
        self, event: AstrMessageEvent, request: ProviderRequest
    ) -> None:
        if request.image_urls and self.settings.vision_model:
            request.model = self.settings.vision_model

    @filter.command("draw", alias={"画图", "生图"})
    async def draw(self, event: AstrMessageEvent, prompt: GreedyStr):
        """使用 OpenAI Compatible Images API 生成一张图片。"""
        event.stop_event()
        if not self.ready:
            yield event.plain_result("AI 图片服务尚未就绪，请稍后重试。")
            return
        try:
            user_id = str(event.get_sender_id())
            if self.permissions.is_super_admin(event):
                user_id = f"admin:{user_id}:{event.get_message_id()}"
            kind, result = await self.service.generate(user_id, str(prompt))
            if kind == "url":
                yield event.chain_result([Comp.Image.fromURL(result)])
            else:
                yield event.chain_result([Comp.Image.fromFileSystem(result)])
        except (ValueError, RuntimeError) as exc:
            yield event.plain_result(str(exc))
        except httpx.HTTPStatusError as exc:
            logger.warning("生图 API 返回错误 status=%s", exc.response.status_code)
            yield event.plain_result("生图服务返回错误，请检查模型、地址或 API Key。")
        except httpx.HTTPError:
            logger.exception("生图网络请求失败")
            yield event.plain_result("暂时无法连接生图服务，请稍后重试。")
        except Exception:
            logger.exception("生成图片失败")
            yield event.plain_result("生成图片失败，请稍后重试。")

    @filter.command("randompic", alias={"随机图片", "来张图"})
    async def random_picture(self, event: AstrMessageEvent):
        """从只读挂载的本地图库随机发送一张图片。"""
        event.stop_event()
        if not self.settings.local_random_enabled:
            yield event.plain_result("本地随机图片功能已禁用。")
            return
        try:
            path = await asyncio.to_thread(
                choose_local_image,
                self.settings.local_random_dir,
                recursive=self.settings.local_random_recursive,
            )
            yield event.chain_result([Comp.Image.fromFileSystem(str(path))])
        except ValueError as exc:
            yield event.plain_result(str(exc))
        except PermissionError:
            logger.exception("读取本地随机图片时权限不足")
            yield event.plain_result("机器人没有读取随机图片目录的权限。")
        except OSError:
            logger.exception("读取本地随机图片失败")
            yield event.plain_result("读取随机图片失败，请检查目录挂载和文件权限。")

    async def terminate(self) -> None:
        self.ready = False
        await self.service.close()
