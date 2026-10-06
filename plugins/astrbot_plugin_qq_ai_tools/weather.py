"""Open-Meteo 实时天气客户端。"""

from __future__ import annotations

import httpx


WEATHER_CODES = {
    0: "晴",
    1: "大致晴朗",
    2: "局部多云",
    3: "阴",
    45: "雾",
    48: "雾凇",
    51: "小毛毛雨",
    53: "毛毛雨",
    55: "强毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    80: "阵雨",
    81: "较强阵雨",
    82: "强阵雨",
    95: "雷暴",
    96: "雷暴伴小冰雹",
    99: "雷暴伴大冰雹",
}


class WeatherService:
    def __init__(self, timeout: int) -> None:
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(timeout), follow_redirects=True)

    async def current(self, location: str) -> str:
        query = location.strip()
        if not 1 <= len(query) <= 100:
            raise ValueError("地点必须为 1～100 个字符。")
        geo = await self.client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": query, "count": 1, "language": "zh", "format": "json"},
        )
        geo.raise_for_status()
        places = geo.json().get("results") or []
        if not places:
            raise ValueError("没有找到这个地点，请补充省份或国家。")
        place = places[0]
        forecast = await self.client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "timezone": "auto",
                "forecast_days": 3,
            },
        )
        forecast.raise_for_status()
        data = forecast.json()
        current = data.get("current") or {}
        daily = data.get("daily") or {}
        name = "，".join(str(v) for v in (place.get("country"), place.get("admin1"), place.get("name")) if v)
        code = int(current.get("weather_code", -1))
        lines = [
            f"🌦️ {name}",
            f"当前：{WEATHER_CODES.get(code, f'天气代码 {code}')}，{current.get('temperature_2m', '?')}°C",
            f"体感：{current.get('apparent_temperature', '?')}°C；湿度：{current.get('relative_humidity_2m', '?')}%；风速：{current.get('wind_speed_10m', '?')} km/h",
        ]
        dates = daily.get("time") or []
        highs = daily.get("temperature_2m_max") or []
        lows = daily.get("temperature_2m_min") or []
        rain = daily.get("precipitation_probability_max") or []
        for date, low, high, probability in list(zip(dates, lows, highs, rain))[:3]:
            lines.append(f"{date}：{low}～{high}°C，最高降水概率 {probability}%")
        lines.append("数据：Open-Meteo")
        return "\n".join(lines)

    async def close(self) -> None:
        await self.client.aclose()
