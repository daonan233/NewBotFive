from __future__ import annotations

import unittest

from plugins.astrbot_plugin_qq_ai_fun.commands import (
    parse_choices,
    parse_lottery_command,
    validate_dice_sides,
)


class LotteryCommandTests(unittest.TestCase):
    def test_parses_prize_with_spaces(self) -> None:
        command = parse_lottery_command("start 2 一箱 可乐", 10)
        self.assertEqual(command.action, "start")
        self.assertEqual(command.winner_count, 2)
        self.assertEqual(command.prize, "一箱 可乐")

    def test_supports_chinese_actions(self) -> None:
        self.assertEqual(parse_lottery_command("参加", 10).action, "join")
        self.assertEqual(parse_lottery_command("开奖", 10).action, "draw")

    def test_rejects_excessive_winners(self) -> None:
        with self.assertRaisesRegex(ValueError, "1 到 3"):
            parse_lottery_command("start 4 奖品", 3)


class MiniGameTests(unittest.TestCase):
    def test_choices_are_trimmed(self) -> None:
        self.assertEqual(parse_choices("苹果 | 香蕉| 梨"), ("苹果", "香蕉", "梨"))

    def test_requires_two_choices(self) -> None:
        with self.assertRaises(ValueError):
            parse_choices("苹果")

    def test_validates_dice_sides(self) -> None:
        self.assertEqual(validate_dice_sides(20), 20)
        with self.assertRaises(ValueError):
            validate_dice_sides(1)


if __name__ == "__main__":
    unittest.main()

