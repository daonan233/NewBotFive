"""用户提醒时间解析；所有结果都转换为带时区时间。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class ParsedReminder:
    trigger_time: datetime
    content: str


_RELATIVE = re.compile(r"^(\d{1,5})\s*(分钟|小时|天)后\s+(.+)$", re.S)
_ABSOLUTE = re.compile(
    r"^(?:(今天|明天)\s+|(\d{4})-(\d{1,2})-(\d{1,2})\s+|"
    r"(\d{1,2})-(\d{1,2})\s+)(\d{1,2}):(\d{2})\s+(.+)$",
    re.S,
)


def parse_reminder(text: str, timezone_name: str, now: datetime | None = None) -> ParsedReminder:
    value = text.strip()
    if not value:
        raise ValueError("用法：/remind 10分钟后 喝水，或 /remind 2026-10-10 15:00 开会")
    zone = ZoneInfo(timezone_name)
    current = now.astimezone(zone) if now else datetime.now(zone)

    relative = _RELATIVE.match(value)
    if relative:
        amount = int(relative.group(1))
        if amount <= 0:
            raise ValueError("提醒时间必须晚于现在。")
        unit = relative.group(2)
        delta = {
            "分钟": timedelta(minutes=amount),
            "小时": timedelta(hours=amount),
            "天": timedelta(days=amount),
        }[unit]
        return ParsedReminder(current + delta, _content(relative.group(3)))

    absolute = _ABSOLUTE.match(value)
    if not absolute:
        raise ValueError(
            "无法识别时间。示例：/remind 10分钟后 喝水；"
            "/remind 明天 09:00 签到；/remind 2026-10-10 15:00 开会"
        )
    relative_day, year, month, day, short_month, short_day, hour, minute, content = (
        absolute.groups()
    )
    if relative_day:
        date = current.date() + timedelta(days=1 if relative_day == "明天" else 0)
        year, month, day = date.year, date.month, date.day
    elif short_month:
        year, month, day = current.year, int(short_month), int(short_day)
    else:
        year, month, day = int(year), int(month), int(day)
    try:
        trigger = datetime(int(year), int(month), int(day), int(hour), int(minute), tzinfo=zone)
    except ValueError as exc:
        raise ValueError("日期或时间无效，请检查月份、日期、小时和分钟。") from exc
    if trigger <= current:
        raise ValueError("提醒时间必须晚于现在。")
    return ParsedReminder(trigger, _content(content))


def _content(value: str) -> str:
    content = value.strip()
    if not content:
        raise ValueError("提醒内容不能为空。")
    if len(content) > 500:
        raise ValueError("提醒内容不能超过 500 个字符。")
    return content

