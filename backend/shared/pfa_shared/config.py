from __future__ import annotations 

import os
from dataclasses import dataclass

from pfa_shared.enums import AppEnv


@dataclass(frozen=True, slots=True)
class CommonSettings:
    app_env: AppEnv
    log_level: str
    redis_url: str

    @classmethod
    def from_env(cls) -> "CommonSettings":
        env_value = os.getenv("APP_ENV", AppEnv.LOCAL.value)
        app_env = AppEnv.from_value(env_value)
        return cls(
            app_env=app_env,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        )
