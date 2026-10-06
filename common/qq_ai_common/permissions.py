"""统一权限判断，避免每个插件重复解析超级管理员配置。"""

from __future__ import annotations

import os
from enum import IntEnum
from typing import Protocol


class PermissionEvent(Protocol):
    def get_sender_id(self) -> str: ...

    def is_admin(self) -> bool: ...


class PermissionLevel(IntEnum):
    USER = 0
    GROUP_ADMIN = 1
    SUPER_ADMIN = 2


class PermissionService:
    def __init__(self, super_users: frozenset[str]) -> None:
        self.super_users = super_users

    @classmethod
    def from_env(cls) -> "PermissionService":
        users = frozenset(
            item.strip()
            for item in os.getenv("SUPER_USERS", "").split(",")
            if item.strip()
        )
        return cls(users)

    def level(self, event: PermissionEvent) -> PermissionLevel:
        if str(event.get_sender_id()) in self.super_users:
            return PermissionLevel.SUPER_ADMIN
        if event.is_admin():
            return PermissionLevel.GROUP_ADMIN
        return PermissionLevel.USER

    def is_admin(self, event: PermissionEvent) -> bool:
        return self.level(event) >= PermissionLevel.GROUP_ADMIN

    def is_super_admin(self, event: PermissionEvent) -> bool:
        return self.level(event) == PermissionLevel.SUPER_ADMIN

    def require_admin(self, event: PermissionEvent) -> None:
        if not self.is_admin(event):
            raise PermissionError("只有群管理员、群主或机器人超级管理员可以执行此操作。")

    def require_super_admin(self, event: PermissionEvent) -> None:
        if not self.is_super_admin(event):
            raise PermissionError("只有机器人超级管理员可以执行此操作。")

