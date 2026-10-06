from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins"))

from astrbot_plugin_qq_ai_media.local_gallery import (  # noqa: E402
    choose_local_image,
    list_local_images,
)


class LocalGalleryTests(unittest.TestCase):
    def test_filters_extensions_and_recurses(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.JPG").write_bytes(b"a")
            (root / "ignore.txt").write_text("x", encoding="utf-8")
            (root / "nested").mkdir()
            (root / "nested" / "b.png").write_bytes(b"b")

            names = {path.name for path in list_local_images(directory)}

            self.assertEqual(names, {"a.JPG", "b.png"})

    def test_non_recursive_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "top.gif").write_bytes(b"a")
            (root / "nested").mkdir()
            (root / "nested" / "hidden.webp").write_bytes(b"b")

            images = list_local_images(directory, recursive=False)

            self.assertEqual([path.name for path in images], ["top.gif"])

    def test_empty_and_missing_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "没有可发送"):
                choose_local_image(directory)
        with self.assertRaisesRegex(ValueError, "目录不存在"):
            choose_local_image("Z:/definitely-not-present/qq-ai-gallery")


if __name__ == "__main__":
    unittest.main()
