"""OpenAI Compatible 生图服务与 Redis 限流。"""

from __future__ import annotations

import base64
import binascii
import secrets
import time
from pathlib import Path
import httpx
from redis.asyncio import ConnectionPool, Redis

from .config import MediaSettings
from .response import detect_image_suffix, parse_image_response


MAX_IMAGE_BYTES = 20 * 1024 * 1024


class ImageService:
    def __init__(self, settings: MediaSettings) -> None:
        self.settings = settings
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.timeout_seconds), follow_redirects=True
        )
        self._pool: ConnectionPool | None = None
        self._redis: Redis | None = None

    async def start(self) -> None:
        self._pool = ConnectionPool.from_url(
            self.settings.redis_url, max_connections=10, decode_responses=True
        )
        self._redis = Redis(connection_pool=self._pool)
        await self._redis.ping()

    async def generate(self, user_id: str, prompt: str) -> tuple[str, str]:
        value = prompt.strip()
        if not 2 <= len(value) <= 1000:
            raise ValueError("生图描述必须为 2～1000 个字符。")
        if not (
            self.settings.image_api_base
            and self.settings.image_api_key
            and self.settings.image_model
        ):
            raise RuntimeError(
                "AI 生图尚未配置，请设置 IMAGE_API_BASE、IMAGE_API_KEY 和 IMAGE_MODEL。"
            )
        await self._consume_quota(user_id)
        response = await self._client.post(
            f"{self.settings.image_api_base}/images/generations",
            headers={"Authorization": f"Bearer {self.settings.image_api_key}"},
            json={
                "model": self.settings.image_model,
                "prompt": value,
                "n": 1,
                "size": "1024x1024",
                # 保持对现有 OpenAI Compatible 服务的 URL 模式兼容；响应收到后
                # 会由 AstrBot 下载到共享目录，再作为本地文件交给 NapCat。
                "response_format": "url",
            },
        )
        response.raise_for_status()
        kind, result = parse_image_response(response.json())
        if kind == "url":
            image, content_type = await self._download_image(result)
            return "file", self._save_image(image, content_type)
        try:
            image = base64.b64decode(result, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise RuntimeError("生图服务返回了无效的 Base64 图片。") from exc
        return "file", self._save_image(image)

    async def _download_image(self, url: str) -> tuple[bytes, str]:
        """下载服务返回的临时图片 URL，不向目标站点转发 API Key。"""
        try:
            async with self._client.stream("GET", url) as response:
                response.raise_for_status()
                declared_size = int(response.headers.get("content-length", "0") or 0)
                if declared_size > MAX_IMAGE_BYTES:
                    raise RuntimeError("生成图片超过 20 MB，已拒绝保存。")
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > MAX_IMAGE_BYTES:
                        raise RuntimeError("生成图片超过 20 MB，已拒绝保存。")
                    chunks.append(chunk)
                return b"".join(chunks), response.headers.get("content-type", "")
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"生图已完成，但临时图片下载失败（HTTP {exc.response.status_code}）。"
            ) from exc
        except httpx.HTTPError as exc:
            raise RuntimeError("生图已完成，但无法下载服务返回的临时图片。") from exc

    def _save_image(self, image: bytes, content_type: str = "") -> str:
        if not image:
            raise RuntimeError("生图服务返回了空图片。")
        if len(image) > MAX_IMAGE_BYTES:
            raise RuntimeError("生成图片超过 20 MB，已拒绝保存。")
        suffix = detect_image_suffix(content_type, image)
        directory = Path(self.settings.output_dir)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{int(time.time())}-{secrets.token_hex(6)}{suffix}"
        path.write_bytes(image)
        return str(path)

    async def _consume_quota(self, user_id: str) -> None:
        if self._redis is None:
            raise RuntimeError("图片限流服务尚未就绪")
        key = f"qqai:rate:image:{user_id}:{int(time.time() // 60)}"
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, 120)
            count, _ = await pipe.execute()
        if int(count) > self.settings.image_rate_limit:
            raise ValueError(
                f"生图太频繁了，每分钟最多 {self.settings.image_rate_limit} 次。"
            )

    async def close(self) -> None:
        await self._client.aclose()
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
        if self._pool is not None:
            await self._pool.aclose()
            self._pool = None
