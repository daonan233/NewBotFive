"""Tavily 与 Serper 搜索供应商适配器。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True, slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str


def parse_tavily(payload: dict[str, Any], limit: int) -> tuple[SearchResult, ...]:
    return tuple(
        SearchResult(
            title=str(item.get("title") or "无标题").strip(),
            url=str(item.get("url") or "").strip(),
            snippet=str(item.get("content") or "").strip(),
        )
        for item in payload.get("results", [])[:limit]
        if item.get("url")
    )


def parse_serper(payload: dict[str, Any], limit: int) -> tuple[SearchResult, ...]:
    return tuple(
        SearchResult(
            title=str(item.get("title") or "无标题").strip(),
            url=str(item.get("link") or "").strip(),
            snippet=str(item.get("snippet") or "").strip(),
        )
        for item in payload.get("organic", [])[:limit]
        if item.get("link")
    )


class SearchProvider:
    def __init__(
        self,
        provider: str,
        api_key: str,
        api_base: str,
        timeout_seconds: int,
    ) -> None:
        self.provider = provider
        self.api_key = api_key
        self.api_base = api_base
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=True,
            headers={"User-Agent": "qq-ai-bot/0.3"},
        )

    async def search(self, query: str, limit: int) -> tuple[SearchResult, ...]:
        if not self.api_key:
            raise RuntimeError(
                "联网搜索尚未配置：请在 .env 设置 SEARCH_API_KEY 和 SEARCH_PROVIDER，"
                "然后重建 AstrBot 容器。"
            )
        if self.provider == "tavily":
            response = await self._client.post(
                f"{self.api_base}/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": limit,
                    "include_answer": False,
                },
            )
            response.raise_for_status()
            return parse_tavily(response.json(), limit)
        response = await self._client.post(
            f"{self.api_base}/search",
            headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
            json={"q": query, "num": limit},
        )
        response.raise_for_status()
        return parse_serper(response.json(), limit)

    async def close(self) -> None:
        await self._client.aclose()

