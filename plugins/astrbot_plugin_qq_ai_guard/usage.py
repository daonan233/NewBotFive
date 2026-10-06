"""兼容多种 OpenAI Compatible 返回格式的 Token 用量提取。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TokenUsageValues:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


def _non_negative(value: object) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def extract_usage(response: object) -> TokenUsageValues:
    usage = getattr(response, "usage", None)
    if usage is not None:
        input_tokens = getattr(usage, "input", None)
        if input_tokens is None:
            input_tokens = getattr(usage, "prompt_tokens", 0)
        output_tokens = getattr(usage, "output", None)
        if output_tokens is None:
            output_tokens = getattr(usage, "completion_tokens", 0)
        return TokenUsageValues(
            prompt_tokens=_non_negative(input_tokens),
            completion_tokens=_non_negative(output_tokens),
        )

    raw = getattr(response, "raw_completion", None)
    raw_usage = getattr(raw, "usage", None)
    if raw_usage is None:
        return TokenUsageValues()
    return TokenUsageValues(
        prompt_tokens=_non_negative(
            getattr(raw_usage, "prompt_tokens", getattr(raw_usage, "input_tokens", 0))
        ),
        completion_tokens=_non_negative(
            getattr(
                raw_usage,
                "completion_tokens",
                getattr(raw_usage, "output_tokens", 0),
            )
        ),
    )


def response_model(response: object, fallback: str = "") -> str:
    raw = getattr(response, "raw_completion", None)
    return str(getattr(raw, "model", "") or fallback or "unknown")

