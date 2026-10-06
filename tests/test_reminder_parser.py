import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins" / "astrbot_plugin_qq_ai_reminder"))

from parser import parse_reminder  # noqa: E402


class ReminderParserTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 6, 12, 0, tzinfo=ZoneInfo("Asia/Shanghai"))

    def test_relative_minutes(self):
        parsed = parse_reminder("10分钟后 喝水", "Asia/Shanghai", self.now)
        self.assertEqual(parsed.trigger_time.hour, 12)
        self.assertEqual(parsed.trigger_time.minute, 10)
        self.assertEqual(parsed.content, "喝水")

    def test_tomorrow(self):
        parsed = parse_reminder("明天 09:30 签到", "Asia/Shanghai", self.now)
        self.assertEqual(parsed.trigger_time.day, 7)
        self.assertEqual(parsed.trigger_time.hour, 9)

    def test_rejects_past_time(self):
        with self.assertRaisesRegex(ValueError, "晚于现在"):
            parse_reminder("2026-10-05 09:00 旧提醒", "Asia/Shanghai", self.now)


if __name__ == "__main__":
    unittest.main()

