"""本地图库扫描与随机选择，独立于 AstrBot 便于测试。"""

from __future__ import annotations

import secrets
from pathlib import Path


SUPPORTED_IMAGE_SUFFIXES = frozenset(
    {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
)


def list_local_images(
    directory: str,
    *,
    recursive: bool = True,
    max_files: int = 100_000,
) -> list[Path]:
    """列出图库中的普通图片文件，不跟随符号链接文件。"""
    root = Path(directory)
    if not root.exists():
        raise ValueError("随机图片目录不存在，请检查 Docker 目录挂载。")
    if not root.is_dir():
        raise ValueError("随机图片路径不是文件夹。")

    iterator = root.rglob("*") if recursive else root.iterdir()
    images: list[Path] = []
    for path in iterator:
        if path.is_symlink() or not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
            continue
        images.append(path)
        if len(images) >= max_files:
            break
    return images


def choose_local_image(directory: str, *, recursive: bool = True) -> Path:
    images = list_local_images(directory, recursive=recursive)
    if not images:
        raise ValueError("随机图片目录中没有可发送的图片。")
    return secrets.choice(images)
