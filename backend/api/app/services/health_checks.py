"""Deep readiness checks cho infra dependencies (M5).

Mỗi check trả về `(name, ok, error)`. Tất cả check đều có timeout ngắn để
endpoint `/health/ready` không block khi 1 service down.

- DB: SELECT 1 qua SQLModel session.
- Redis: `PING` qua `redis.asyncio` (cùng URL với taskiq broker).
- S3: `head_bucket` qua boto3 (chỉ khi `storage_backend == "s3"`).
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import cast

from redis.asyncio import Redis
from sqlalchemy import text
from sqlmodel import Session

from app.core.config import Settings
from app.core.database import engine
from app.core.logging import get_logger

logger = get_logger("api.health_checks")

# Timeout per check (giây). Đủ để Redis/DB respond trong điều kiện bình thường,
# đủ ngắn để /health/ready không hang khi 1 service down.
DEFAULT_CHECK_TIMEOUT_SECONDS = 2.0


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    ok: bool
    error: str | None = None


async def check_database(timeout: float = DEFAULT_CHECK_TIMEOUT_SECONDS) -> CheckResult:
    """Ping DB bằng `SELECT 1`. Sync call wrap trong `asyncio.to_thread`.

    Note: SQLModel/SQLAlchemy sync engine chạy `SELECT 1` rất nhanh; timeout
    chủ yếu để chống treo khi DB unreachable (vd. firewall drop packet).
    """
    def _ping() -> None:
        with Session(engine) as session:
            session.exec(text("SELECT 1"))  # type: ignore[call-overload]

    try:
        await asyncio.wait_for(asyncio.to_thread(_ping), timeout=timeout)
    except TimeoutError:
        return CheckResult(name="database", ok=False, error=f"timeout after {timeout}s")
    except Exception as exc:
        return CheckResult(name="database", ok=False, error=str(exc)[:200])
    return CheckResult(name="database", ok=True)


async def check_redis(
    redis_url: str,
    timeout: float = DEFAULT_CHECK_TIMEOUT_SECONDS,
) -> CheckResult:
    """Ping Redis. Tạo client mới mỗi lần để không reuse stale connection."""
    client: Redis | None = None
    try:
        client = Redis.from_url(redis_url, socket_connect_timeout=timeout)
        # `redis.asyncio.Redis.ping()` trả `Awaitable[bool]` trong async
        # client, nhưng type stub union với sync `bool` → cast cho rõ.
        ping_awaitable = cast("Awaitable[bool]", client.ping())
        await asyncio.wait_for(ping_awaitable, timeout=timeout)
    except TimeoutError:
        return CheckResult(name="redis", ok=False, error=f"timeout after {timeout}s")
    except Exception as exc:
        return CheckResult(name="redis", ok=False, error=str(exc)[:200])
    finally:
        if client is not None:
            try:
                await client.aclose()
            except Exception:  # pragma: no cover - cleanup best effort
                pass
    return CheckResult(name="redis", ok=True)


async def check_s3(
    settings: Settings,
    timeout: float = DEFAULT_CHECK_TIMEOUT_SECONDS,
) -> CheckResult:
    """Head bucket trên S3/MinIO. Chỉ chạy khi `storage_backend == "s3"`.

    Nếu backend là "local", trả `ok=True` với note đặc biệt vì không có infra
    để ping (filesystem luôn available).
    """
    if settings.storage_backend != "s3":
        return CheckResult(name="storage", ok=True, error=None)

    def _head() -> None:
        # Import boto3 lazily — module import path không bị lỗi nếu boto3 missing
        # ở dev env vẫn dùng local storage.
        import boto3  # type: ignore[import-untyped]
        from botocore.client import Config  # type: ignore[import-untyped]

        client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(
                connect_timeout=timeout,
                read_timeout=timeout,
                retries={"max_attempts": 1},
            ),
        )
        client.head_bucket(Bucket=settings.s3_bucket_private)

    try:
        await asyncio.wait_for(asyncio.to_thread(_head), timeout=timeout * 2)
    except TimeoutError:
        return CheckResult(name="storage", ok=False, error=f"timeout after {timeout * 2}s")
    except Exception as exc:
        return CheckResult(name="storage", ok=False, error=str(exc)[:200])
    return CheckResult(name="storage", ok=True)


async def run_readiness_checks(settings: Settings) -> list[CheckResult]:
    """Chạy tất cả checks song song. Trả list theo thứ tự cố định để test
    có thể assert theo index nếu muốn."""
    db_task = asyncio.create_task(check_database())
    redis_task = asyncio.create_task(check_redis(settings.redis_url))
    s3_task = asyncio.create_task(check_s3(settings))

    results = await asyncio.gather(db_task, redis_task, s3_task)
    return list(results)
