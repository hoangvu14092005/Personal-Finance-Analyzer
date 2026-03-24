from __future__ import annotations

from enum import StrEnum


class AppEnv(StrEnum):
    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PROD = "prod"

    @classmethod
    def from_value(cls, value: str) -> "AppEnv":
        normalized = value.strip().lower()
        for member in cls:
            if member.value == normalized:
                return member
        return cls.LOCAL


class ServiceName(StrEnum):
    API = "api"
    WORKER = "worker"
