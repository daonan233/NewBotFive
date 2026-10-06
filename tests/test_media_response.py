import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins"))

from astrbot_plugin_qq_ai_media.response import (  # noqa: E402
    detect_image_suffix,
    parse_image_response,
)


class MediaResponseTests(unittest.TestCase):
    def test_url_response(self):
        self.assertEqual(
            parse_image_response({"data": [{"url": "https://img.test/a.png"}]}),
            ("url", "https://img.test/a.png"),
        )

    def test_base64_response(self):
        self.assertEqual(
            parse_image_response({"data": [{"b64_json": "YWJj"}]}),
            ("base64", "YWJj"),
        )

    def test_missing_image(self):
        with self.assertRaises(RuntimeError):
            parse_image_response({"data": []})

    def test_detect_image_suffix_from_content_type(self):
        self.assertEqual(detect_image_suffix("image/jpeg; charset=binary", b"data"), ".jpg")

    def test_detect_image_suffix_from_magic_bytes(self):
        self.assertEqual(detect_image_suffix("application/octet-stream", b"\x89PNG\r\n\x1a\n"), ".png")

    def test_reject_unknown_image_format(self):
        with self.assertRaises(RuntimeError):
            detect_image_suffix("text/html", b"<html></html>")


if __name__ == "__main__":
    unittest.main()
