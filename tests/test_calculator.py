import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins" / "astrbot_plugin_qq_ai_tools"))

from calculator import calculate  # noqa: E402


class CalculatorTests(unittest.TestCase):
    def test_arithmetic_and_functions(self):
        self.assertEqual(calculate("2 + 3 * 4"), 14)
        self.assertEqual(calculate("sqrt(81)"), 9)

    def test_rejects_code_execution(self):
        with self.assertRaisesRegex(ValueError, "不允许"):
            calculate("__import__('os').system('whoami')")

    def test_limits_exponent(self):
        with self.assertRaisesRegex(ValueError, "指数"):
            calculate("2 ** 101")


if __name__ == "__main__":
    unittest.main()

