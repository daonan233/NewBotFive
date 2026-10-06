"""基础配置单元测试，不需要 AstrBot、PostgreSQL 或 Redis。"""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from plugins.astrbot_plugin_qq_ai_core.config import InfrastructureSettings


VALID_ENV = {
    "POSTGRES_USER": "bot user",
    "POSTGRES_PASSWORD": "p@ss/word",
    "POSTGRES_DB": "qq_ai_bot",
    "POSTGRES_HOST": "postgres",
    "POSTGRES_PORT": "5432",
    "POSTGRES_POOL_MIN_SIZE": "1",
    "POSTGRES_POOL_MAX_SIZE": "10",
    "REDIS_HOST": "redis",
    "REDIS_PORT": "6379",
    "REDIS_DB": "0",
    "REDIS_PASSWORD": "redis secret",
    "REDIS_POOL_MAX_CONNECTIONS": "20",
}


class InfrastructureSettingsTests(unittest.TestCase):
    def test_builds_encoded_connection_urls(self) -> None:
        with patch.dict(os.environ, VALID_ENV, clear=True):
            settings = InfrastructureSettings.from_env()

        self.assertIn("bot+user:p%40ss%2Fword", settings.postgres_dsn)
        self.assertIn(":redis+secret@redis:6379/0", settings.redis_url)
        self.assertEqual(settings.postgres_pool_max_size, 10)

    def test_rejects_inverted_postgres_pool_range(self) -> None:
        invalid = {**VALID_ENV, "POSTGRES_POOL_MIN_SIZE": "11"}
        with patch.dict(os.environ, invalid, clear=True):
            with self.assertRaisesRegex(ValueError, "不能大于"):
                InfrastructureSettings.from_env()

    def test_requires_secrets(self) -> None:
        invalid = {**VALID_ENV, "REDIS_PASSWORD": ""}
        with patch.dict(os.environ, invalid, clear=True):
            with self.assertRaisesRegex(ValueError, "REDIS_PASSWORD"):
                InfrastructureSettings.from_env()


if __name__ == "__main__":
    unittest.main()

