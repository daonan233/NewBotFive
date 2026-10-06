"""无需分类模型的可解释规则路由。"""

from __future__ import annotations

import re


_CODE = re.compile(r"```|\b(traceback|exception|javascript|python|java|sql|html|css|rust|golang)\b|代码|报错|函数|正则", re.I)
_COMPLEX = re.compile(r"详细分析|深入分析|推理|论证|比较|权衡|方案|架构|为什么|证明|规划")


def route_kind(prompt: str) -> str:
    value = (prompt or "").strip()
    if _CODE.search(value):
        return "coding"
    if len(value) >= 180 or _COMPLEX.search(value):
        return "smart"
    if len(value) <= 40:
        return "fast"
    return "default"

