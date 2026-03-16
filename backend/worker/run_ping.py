from __future__ import annotations

import asyncio

from tasks import ping_task


async def main() -> None:
    task = await ping_task.kiq()
    result = await task.wait_result(timeout=5)
    if result.is_err:
        raise RuntimeError(f"ping_task failed: {result.error}")
    print(result.return_value)


if __name__ == "__main__":
    asyncio.run(main())
