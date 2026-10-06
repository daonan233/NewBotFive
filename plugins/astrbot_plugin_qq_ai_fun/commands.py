"""命令文本解析，独立于 AstrBot，便于单元测试。"""

from __future__ import annotations

from dataclasses import dataclass


HELP_TEXT = """抽奖命令：
/lottery start <中奖人数> <奖品>
/lottery join
/lottery status
/lottery draw
/lottery cancel
（查看本帮助：/lottery help）
小游戏：/roll [面数]；/pick 选项A|选项B|选项C"""


@dataclass(frozen=True, slots=True)
class LotteryCommand:
    action: str
    winner_count: int = 1
    prize: str = ""


def parse_lottery_command(raw: str, max_winners: int) -> LotteryCommand:
    text = raw.strip()
    if not text:
        return LotteryCommand(action="help")
    parts = text.split(maxsplit=2)
    action_aliases = {
        "开始": "start",
        "参与": "join",
        "参加": "join",
        "状态": "status",
        "开奖": "draw",
        "取消": "cancel",
        "帮助": "help",
    }
    action = action_aliases.get(parts[0].lower(), parts[0].lower())
    if action != "start":
        if action not in {"join", "status", "draw", "cancel", "help"}:
            raise ValueError("未知抽奖操作。\n" + HELP_TEXT)
        return LotteryCommand(action=action)

    if len(parts) < 3:
        raise ValueError("用法：/lottery start <中奖人数> <奖品>")
    try:
        count = int(parts[1])
    except ValueError as exc:
        raise ValueError("中奖人数必须是整数。") from exc
    if count < 1 or count > max_winners:
        raise ValueError(f"中奖人数必须在 1 到 {max_winners} 之间。")
    prize = parts[2].strip()
    if not prize or len(prize) > 200:
        raise ValueError("奖品不能为空，且不能超过 200 个字符。")
    return LotteryCommand(action="start", winner_count=count, prize=prize)


def parse_choices(raw: str) -> tuple[str, ...]:
    choices = tuple(item.strip() for item in raw.split("|") if item.strip())
    if len(choices) < 2:
        raise ValueError("至少提供两个选项，并使用 | 分隔。")
    if len(choices) > 20:
        raise ValueError("一次最多提供 20 个选项。")
    if any(len(item) > 100 for item in choices):
        raise ValueError("每个选项不能超过 100 个字符。")
    return choices


def validate_dice_sides(sides: int) -> int:
    if sides < 2 or sides > 1000:
        raise ValueError("骰子面数必须在 2 到 1000 之间。")
    return sides
