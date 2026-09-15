"""Centralized runtime environment configuration."""

from __future__ import annotations

import os


class EnvVars:
    """Canonical environment variable names with backward-compatible legacy aliases."""

    ROUTER_API_KEY = "BROWSER_AGENT_ROUTER_API_KEY"
    ROUTER_BASE_URL = "BROWSER_AGENT_ROUTER_BASE_URL"
    ROUTER_MODEL = "BROWSER_AGENT_ROUTER_MODEL"
    FALLBACK_MODEL = "BROWSER_AGENT_FALLBACK_MODEL"
    LOCALE = "BROWSER_AGENT_LOCALE"
    TIMEZONE = "BROWSER_AGENT_TIMEZONE"
    CURRENCY = "BROWSER_AGENT_CURRENCY"
    COUNTRY = "BROWSER_AGENT_COUNTRY"


def getenv(name: str, *legacy_names: str, default: str = "") -> str:
    """Read a canonical variable, falling back to explicitly supported legacy names."""
    value = os.getenv(name, "").strip()
    if value:
        return value
    for legacy in legacy_names:
        value = os.getenv(legacy, "").strip()
        if value:
            return value
    return default
