from __future__ import annotations

import pytest
from app.core.config import ROOT_ENV_FILE


def _read_env_file(path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def test_api_settings_can_load_root_env_file() -> None:
    if not ROOT_ENV_FILE.exists():
        pytest.skip("root .env is intentionally local-only")

    settings = _read_env_file(ROOT_ENV_FILE)

    assert settings["DATABASE_URL"] == "postgresql+psycopg://pfa:pfa@localhost:5434/pfa"
    assert settings["STORAGE_BACKEND"] == "s3"
    assert settings["OCR_PROVIDER"] == "llm_vision"
    assert settings["CHAT_LLM_BASE_URL"] == "http://localhost:20128/v1"
    assert settings["CHAT_LLM_MODEL"] == "cx/gpt-5.5"
    assert settings["CHAT_LLM_API_KEY"].startswith("sk-")


def test_root_env_example_documents_required_runtime_keys() -> None:
    example_path = ROOT_ENV_FILE.with_name(".env.example")
    content = example_path.read_text(encoding="utf-8")

    for key in [
        "DATABASE_URL",
        "REDIS_URL",
        "NEXT_PUBLIC_API_BASE_URL",
        "STORAGE_BACKEND",
        "OCR_PROVIDER",
        "CHAT_LLM_BASE_URL",
        "CHAT_LLM_API_KEY",
        "CHAT_LLM_MODEL",
    ]:
        assert f"{key}=" in content
