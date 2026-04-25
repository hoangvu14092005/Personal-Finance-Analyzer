"""Unit tests cho `Settings._enforce_production_secrets` (M5 fail-fast).

Test trực tiếp class `Settings` — không qua `get_settings()` để bỏ qua cache.
Pydantic raises `ValidationError` khi model_validator fail.
"""
from __future__ import annotations

import pytest
from app.core.config import DEFAULT_JWT_SECRET, MIN_JWT_SECRET_LENGTH, Settings
from pfa_shared.enums import AppEnv
from pydantic import ValidationError


def _kwargs_with(**overrides: object) -> dict[str, object]:
    """Helper build kwargs Settings, sử dụng pydantic-settings env_file=None
    để tránh đọc .env trong CI/test."""
    base: dict[str, object] = {
        "_env_file": None,
    }
    base.update(overrides)
    return base


class TestLocalEnv:
    def test_local_with_default_secret_passes(self) -> None:
        settings = Settings(**_kwargs_with(app_env=AppEnv.LOCAL))
        assert settings.jwt_secret == DEFAULT_JWT_SECRET
        assert settings.storage_backend == "local"

    def test_test_env_with_default_secret_passes(self) -> None:
        settings = Settings(**_kwargs_with(app_env=AppEnv.TEST))
        assert settings.app_env == AppEnv.TEST


class TestStagingProdEnv:
    @pytest.mark.parametrize("env", [AppEnv.STAGING, AppEnv.PROD])
    def test_default_jwt_secret_rejected(self, env: AppEnv) -> None:
        with pytest.raises(ValidationError, match="JWT_SECRET must be set"):
            Settings(
                **_kwargs_with(
                    app_env=env,
                    jwt_secret=DEFAULT_JWT_SECRET,
                    storage_backend="s3",
                ),
            )

    @pytest.mark.parametrize("env", [AppEnv.STAGING, AppEnv.PROD])
    def test_short_jwt_secret_rejected(self, env: AppEnv) -> None:
        short_secret = "x" * (MIN_JWT_SECRET_LENGTH - 1)
        with pytest.raises(ValidationError, match="at least"):
            Settings(
                **_kwargs_with(
                    app_env=env,
                    jwt_secret=short_secret,
                    storage_backend="s3",
                ),
            )

    @pytest.mark.parametrize("env", [AppEnv.STAGING, AppEnv.PROD])
    def test_local_storage_rejected(self, env: AppEnv) -> None:
        long_secret = "a" * 64
        with pytest.raises(ValidationError, match="STORAGE_BACKEND"):
            Settings(
                **_kwargs_with(
                    app_env=env,
                    jwt_secret=long_secret,
                    storage_backend="local",
                ),
            )

    @pytest.mark.parametrize("env", [AppEnv.STAGING, AppEnv.PROD])
    def test_valid_production_config_passes(self, env: AppEnv) -> None:
        long_secret = "a" * 64
        settings = Settings(
            **_kwargs_with(
                app_env=env,
                jwt_secret=long_secret,
                storage_backend="s3",
            ),
        )
        assert settings.jwt_secret == long_secret
        assert settings.storage_backend == "s3"

    def test_exact_min_length_secret_passes(self) -> None:
        secret = "a" * MIN_JWT_SECRET_LENGTH
        settings = Settings(
            **_kwargs_with(
                app_env=AppEnv.PROD,
                jwt_secret=secret,
                storage_backend="s3",
            ),
        )
        assert len(settings.jwt_secret) == MIN_JWT_SECRET_LENGTH
