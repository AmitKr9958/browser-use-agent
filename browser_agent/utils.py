"""Shared asynchronous utilities for Browser Agent runtime code."""

from __future__ import annotations

import inspect
from typing import Any


async def await_if_needed(value: Any) -> Any:
    """Await a value when it is awaitable; otherwise return it unchanged."""
    if inspect.isawaitable(value):
        return await value
    return value
