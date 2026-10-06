"""生图 API 响应解析，不依赖网络客户端。"""

from __future__ import annotations

from typing import Any


_CONTENT_TYPE_SUFFIXES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
}


def parse_image_response(payload: dict[str, Any]) -> tuple[str, str]:
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        raise RuntimeError("生图服务没有返回图片。")
    item = data[0]
    if not isinstance(item, dict):
        raise RuntimeError("生图服务返回格式无效。")
    url = str(item.get("url") or "").strip()
    if url:
        return "url", url
    encoded = str(item.get("b64_json") or "").strip()
    if encoded:
        return "base64", encoded
    raise RuntimeError("生图服务没有返回可用的 URL 或 Base64 图片。")


def detect_image_suffix(content_type: str, data: bytes) -> str:
    """根据响应类型和文件头识别 QQ/NapCat 可发送的图片格式。"""
    media_type = content_type.partition(";")[0].strip().lower()
    if media_type in _CONTENT_TYPE_SUFFIXES:
        return _CONTENT_TYPE_SUFFIXES[media_type]
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data.startswith(b"BM"):
        return ".bmp"
    raise RuntimeError("生图服务返回的内容不是受支持的图片格式。")
