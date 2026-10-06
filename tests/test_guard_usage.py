from __future__ import annotations

import unittest
from types import SimpleNamespace

from plugins.astrbot_plugin_qq_ai_guard.usage import (
    extract_usage,
    response_model,
)


class GuardUsageTests(unittest.TestCase):
    def test_extracts_current_astrbot_usage(self) -> None:
        response = SimpleNamespace(
            usage=SimpleNamespace(input=12, output=5), raw_completion=None
        )
        usage = extract_usage(response)
        self.assertEqual(usage.prompt_tokens, 12)
        self.assertEqual(usage.completion_tokens, 5)
        self.assertEqual(usage.total_tokens, 17)

    def test_falls_back_to_openai_raw_usage(self) -> None:
        raw = SimpleNamespace(
            model="gpt-test",
            usage=SimpleNamespace(prompt_tokens=20, completion_tokens=7),
        )
        response = SimpleNamespace(usage=None, raw_completion=raw)
        usage = extract_usage(response)
        self.assertEqual((usage.prompt_tokens, usage.completion_tokens), (20, 7))
        self.assertEqual(response_model(response), "gpt-test")

    def test_missing_usage_is_zero(self) -> None:
        response = SimpleNamespace(usage=None, raw_completion=None)
        self.assertEqual(extract_usage(response).total_tokens, 0)
        self.assertEqual(response_model(response, "fallback"), "fallback")


if __name__ == "__main__":
    unittest.main()

