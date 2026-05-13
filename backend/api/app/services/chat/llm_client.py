"""OpenAI-compatible LLM client (Phase 6.2).

Async HTTP client cho chat completions API. Hỗ trợ:
- Function calling (tools + tool_choice)
- Streaming SSE
- Retry 1 lần cho network errors
- Logging (redact API key)
"""
from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.logging import get_logger

logger = get_logger("api.chat.llm")


class LLMClientError(Exception):
    """Lỗi khi gọi LLM."""


class OpenAICompatClient:
    """Client cho OpenAI-compatible chat completions endpoint."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout_seconds
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str = "auto",
        stream: bool = False,
    ) -> dict[str, Any] | AsyncIterator[dict[str, Any]]:
        """Gọi /chat/completions.

        stream=False: return full response dict.
        stream=True: return async generator yielding parsed SSE delta dicts.

        Raises:
            LLMClientError: network error, timeout, hoặc non-2xx response.
        """
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = tool_choice

        start = time.perf_counter()
        logger.info(
            "llm.request_start model=%s messages=%d has_tools=%s stream=%s",
            self.model,
            len(messages),
            bool(tools),
            stream,
        )

        if stream:
            return await self._stream_request(body, start)
        return await self._sync_request(body, start)

    async def _sync_request(
        self,
        body: dict[str, Any],
        start: float,
    ) -> dict[str, Any]:
        """Non-streaming request with 1 retry."""
        url = f"{self.base_url}/chat/completions"
        response = await self._request_with_retry(url, body)

        elapsed_ms = (time.perf_counter() - start) * 1000
        data = response.json()

        tokens = data.get("usage", {})
        logger.info(
            "llm.request_end status=%d duration_ms=%.1f prompt_tokens=%s completion_tokens=%s",
            response.status_code,
            elapsed_ms,
            tokens.get("prompt_tokens"),
            tokens.get("completion_tokens"),
        )
        return data  # type: ignore[no-any-return]

    async def _stream_request(
        self,
        body: dict[str, Any],
        start: float,
    ) -> AsyncIterator[dict[str, Any]]:
        """Streaming request — yields parsed SSE chunks."""
        url = f"{self.base_url}/chat/completions"

        async def _generator() -> AsyncIterator[dict[str, Any]]:
            try:
                async with self._client.stream(
                    "POST",
                    url,
                    json=body,
                ) as response:
                    if response.status_code >= 400:
                        error_body = await response.aread()
                        raise LLMClientError(
                            f"LLM returned {response.status_code}: {error_body.decode()[:200]}",
                        )

                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            yield chunk
                        except json.JSONDecodeError:
                            continue
            except httpx.TimeoutException as exc:
                raise LLMClientError(f"LLM timeout: {exc}") from exc
            except httpx.NetworkError as exc:
                raise LLMClientError(f"LLM network error: {exc}") from exc
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                logger.info("llm.stream_end duration_ms=%.1f", elapsed_ms)

        return _generator()

    async def _request_with_retry(
        self,
        url: str,
        body: dict[str, Any],
        max_retries: int = 1,
    ) -> httpx.Response:
        """POST with 1 retry for network/timeout errors. No retry for 4xx."""
        last_exc: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                response = await self._client.post(url, json=body)
                if response.status_code >= 400:
                    raise LLMClientError(
                        f"LLM returned {response.status_code}: "
                        f"{response.text[:200]}",
                    )
                return response
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exc = exc
                if attempt < max_retries:
                    logger.warning(
                        "llm.retry attempt=%d error=%s",
                        attempt + 1,
                        str(exc)[:100],
                    )
                    import asyncio
                    await asyncio.sleep(1.0)
                    continue
                raise LLMClientError(
                    f"LLM request failed after {max_retries + 1} attempts: {exc}",
                ) from exc
        # Should not reach here
        raise LLMClientError(f"LLM request failed: {last_exc}")  # pragma: no cover

    async def close(self) -> None:
        """Close underlying HTTP client."""
        await self._client.aclose()


__all__ = ["LLMClientError", "OpenAICompatClient"]
