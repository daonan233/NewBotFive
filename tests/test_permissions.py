from __future__ import annotations

import unittest

from common.qq_ai_common.permissions import PermissionLevel, PermissionService


class FakeEvent:
    def __init__(self, user_id: str, admin: bool = False) -> None:
        self.user_id = user_id
        self.admin = admin

    def get_sender_id(self) -> str:
        return self.user_id

    def is_admin(self) -> bool:
        return self.admin


class PermissionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.permissions = PermissionService(frozenset({"10001"}))

    def test_super_user_has_highest_level(self) -> None:
        self.assertEqual(
            self.permissions.level(FakeEvent("10001")),
            PermissionLevel.SUPER_ADMIN,
        )

    def test_group_admin_is_admin(self) -> None:
        self.assertTrue(self.permissions.is_admin(FakeEvent("20002", admin=True)))

    def test_regular_user_is_rejected(self) -> None:
        with self.assertRaises(PermissionError):
            self.permissions.require_admin(FakeEvent("30003"))


if __name__ == "__main__":
    unittest.main()

