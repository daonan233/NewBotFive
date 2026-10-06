import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins" / "astrbot_plugin_qq_ai_search"))

from providers import parse_serper, parse_tavily  # noqa: E402


class SearchProviderParserTests(unittest.TestCase):
    def test_parse_tavily(self):
        results = parse_tavily(
            {"results": [{"title": "A", "url": "https://a.test", "content": "摘要"}]},
            5,
        )
        self.assertEqual(results[0].title, "A")
        self.assertEqual(results[0].snippet, "摘要")

    def test_parse_serper_ignores_missing_links(self):
        results = parse_serper(
            {"organic": [{"title": "无链接"}, {"title": "B", "link": "https://b.test"}]},
            5,
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].url, "https://b.test")


if __name__ == "__main__":
    unittest.main()

