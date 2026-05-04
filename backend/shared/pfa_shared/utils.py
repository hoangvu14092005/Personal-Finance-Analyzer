"""Utility functions dùng chung."""
from __future__ import annotations


def normalize_whitespace(value: str) -> str:
    """Normalize multiple spaces/tabs/newlines thành single space.
    
    Examples:
        "hello  world" -> "hello world"
        "hello\\n\\tworld" -> "hello world"
    """
    return " ".join(value.split())
