"""Indian-market runtime defaults for Browser Agent tasks.

These settings are intentionally application-level: Browser Harness owns the Chrome
profile, so we do not mutate an existing user's browser locale or timezone.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IndiaRuntimeConfig:
    """Regional conventions used when an agent handles Indian websites/forms."""

    locale: str = "en-IN"
    timezone: str = "Asia/Kolkata"
    currency: str = "INR"
    country_code: str = "IN"

    @classmethod
    def from_environment(cls) -> "IndiaRuntimeConfig":
        """Load safe regional overrides from environment variables."""
        return cls(
            locale=os.getenv("BROWSER_AGENT_LOCALE", cls.locale),
            timezone=os.getenv("BROWSER_AGENT_TIMEZONE", cls.timezone),
            currency=os.getenv("BROWSER_AGENT_CURRENCY", cls.currency),
            country_code=os.getenv("BROWSER_AGENT_COUNTRY", cls.country_code),
        )

    def instruction(self) -> str:
        """Return concise regional guidance suitable for an agent task."""
        return (
            "Use Indian regional conventions where the website asks for them: "
            f"country={self.country_code}, locale={self.locale}, timezone={self.timezone}, "
            f"currency={self.currency}. Never invent an Indian address, identity, tax ID, "
            "phone number, OTP, or other personal value; use the user's supplied data."
        )


DEFAULT_INDIA_RUNTIME = IndiaRuntimeConfig()
