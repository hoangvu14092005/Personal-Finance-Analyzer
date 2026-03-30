from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    currency: str = Field(default="VND", min_length=3, max_length=10)
    timezone: str = Field(default="Asia/Ho_Chi_Minh", max_length=64)
    locale: str = Field(default="vi-VN", max_length=16)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        has_alpha = any(ch.isalpha() for ch in value)
        has_digit = any(ch.isdigit() for ch in value)
        if not has_alpha or not has_digit:
            raise ValueError("Password must include both letters and digits")
        return value


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class ProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    email: EmailStr
    full_name: str | None
    currency: str
    timezone: str
    locale: str


class AuthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user: ProfileResponse
