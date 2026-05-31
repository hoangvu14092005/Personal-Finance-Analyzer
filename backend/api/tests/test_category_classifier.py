"""Unit tests cho category_classifier parsing (G1 — không gọi LLM thật)."""
from __future__ import annotations

from app.services.category_classifier import _parse_category_id


def test_parse_valid_json() -> None:
    assert _parse_category_id('{"category_id": 3}', {1, 2, 3}) == 3


def test_parse_null_returns_none() -> None:
    assert _parse_category_id('{"category_id": null}', {1, 2, 3}) is None


def test_parse_rejects_id_not_in_list() -> None:
    # Chống bịa: id 99 không nằm trong valid_ids.
    assert _parse_category_id('{"category_id": 99}', {1, 2, 3}) is None


def test_parse_strips_markdown_fences() -> None:
    content = '```json\n{"category_id": 2}\n```'
    assert _parse_category_id(content, {1, 2, 3}) == 2


def test_parse_bare_number_fallback() -> None:
    assert _parse_category_id("3", {1, 2, 3}) == 3


def test_parse_bare_number_not_in_list() -> None:
    assert _parse_category_id("42", {1, 2, 3}) is None


def test_parse_garbage_returns_none() -> None:
    assert _parse_category_id("tôi không biết", {1, 2, 3}) is None


def test_parse_string_id_coerced() -> None:
    assert _parse_category_id('{"category_id": "2"}', {1, 2, 3}) == 2
