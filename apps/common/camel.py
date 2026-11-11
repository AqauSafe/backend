"""Recursive snake_case <-> camelCase helpers for the API boundary."""

from __future__ import annotations

import re
from typing import Any

_FIRST_CAP_RE = re.compile(r"(.)([A-Z][a-z]+)")
_ALL_CAP_RE = re.compile(r"([a-z0-9])([A-Z])")


def to_snake_case(name: str) -> str:
    intermediate = _FIRST_CAP_RE.sub(r"\1_\2", name)
    return _ALL_CAP_RE.sub(r"\1_\2", intermediate).lower()


def to_camel_case(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def camelize(value: Any) -> Any:
    if isinstance(value, dict):
        return {to_camel_case(str(key)): camelize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [camelize(item) for item in value]
    return value


def snakeize(value: Any) -> Any:
    if isinstance(value, dict):
        return {to_snake_case(str(key)): snakeize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [snakeize(item) for item in value]
    return value
