import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins" / "astrbot_plugin_qq_ai_fun"))

from routing import route_kind  # noqa: E402


class ModelRoutingTests(unittest.TestCase):
    def test_code_has_priority(self):
        self.assertEqual(route_kind("请帮我修复这段 Python 代码"), "coding")

    def test_complex_and_fast(self):
        self.assertEqual(route_kind("请详细分析两种架构的权衡"), "smart")
        self.assertEqual(route_kind("你好"), "fast")


if __name__ == "__main__":
    unittest.main()

