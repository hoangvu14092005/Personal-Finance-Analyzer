from __future__ import annotations

from pathlib import Path

# Load root .env before CommonSettings.from_env() reads os.environ.
# Must run BEFORE importing pfa_shared.config.
try:
    from dotenv import load_dotenv

    _root_env_path = Path(__file__).resolve().parents[2] / ".env"
    _legacy_env_path = Path(__file__).parent / ".env"
    if _root_env_path.exists():
        load_dotenv(_root_env_path)
    elif _legacy_env_path.exists():
        load_dotenv(_legacy_env_path)
except ImportError:
    # dotenv optional — fallback to shell env vars
    pass

from pfa_shared.config import CommonSettings  # noqa: E402
from pfa_shared.logging import get_logger  # noqa: E402
from sqlmodel import create_engine  # noqa: E402
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend  # noqa: E402

settings = CommonSettings.from_env()
logger = get_logger("worker", level=settings.log_level)
logger.info("Initializing worker broker")

broker = ListQueueBroker(url=settings.redis_url).with_result_backend(
    RedisAsyncResultBackend(redis_url=settings.redis_url),
)

# Engine dùng chung ở phạm vi process. Worker là long-lived process xử lý nhiều
# task; tạo `create_engine` trong mỗi task sẽ rò rỉ connection pool. Dùng một
# engine duy nhất + pool_pre_ping (phát hiện connection chết sau idle) +
# pool_recycle (recycle sau 30 phút để né server-side idle timeout).
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
)
