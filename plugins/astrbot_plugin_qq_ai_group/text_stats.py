"""无需外部分词服务的轻量关键词统计。"""

from __future__ import annotations

import re
from collections import Counter


_ASCII_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_+#.-]{1,31}")
_CHINESE = re.compile(r"[\u4e00-\u9fff]{2,}")
_STOPWORDS = {
    "我们",
    "你们",
    "他们",
    "这个",
    "那个",
    "什么",
    "怎么",
    "可以",
    "还是",
    "就是",
    "不是",
    "没有",
    "一个",
    "一下",
    "然后",
    "感觉",
    "今天",
    "现在",
}


def top_keywords(messages: list[str], limit: int = 5) -> tuple[str, ...]:
    counter: Counter[str] = Counter()
    for message in messages:
        for word in _ASCII_WORD.findall(message):
            normalized = word.lower()
            if not normalized.startswith("http"):
                counter[normalized] += 1
        for run in _CHINESE.findall(message):
            if run in _STOPWORDS:
                continue
            # 中文没有额外分词依赖时使用二元词组，短而稳定。
            for index in range(len(run) - 1):
                token = run[index : index + 2]
                if token not in _STOPWORDS:
                    counter[token] += 1
    return tuple(word for word, _ in counter.most_common(max(1, limit)))

