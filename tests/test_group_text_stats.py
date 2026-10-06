from __future__ import annotations

import unittest

from plugins.astrbot_plugin_qq_ai_group.text_stats import top_keywords


class GroupTextStatsTests(unittest.TestCase):
    def test_counts_ascii_words_case_insensitively(self) -> None:
        result = top_keywords(["Python 很好", "python 真好", "Python bot"])
        self.assertEqual(result[0], "python")

    def test_returns_chinese_bigrams(self) -> None:
        result = top_keywords(["人工智能很好", "人工智能发展很快"])
        self.assertIn("人工", result)

    def test_empty_messages(self) -> None:
        self.assertEqual(top_keywords([]), ())


if __name__ == "__main__":
    unittest.main()

