"""Indian-market runtime defaults for Browser Agent tasks."""

from __future__ import annotations

from dataclasses import dataclass

from browser_agent.config import EnvVars, getenv


@dataclass(frozen=True, slots=True)
class IndiaRuntimeConfig:
    """Regional conventions used when an agent handles Indian websites/forms."""

    locale: str = "en-IN"
    timezone: str = "Asia/Kolkata"
    currency: str = "INR"
    country_code: str = "IN"

    @classmethod
    def from_environment(cls) -> "IndiaRuntimeConfig":
        """Load safe regional overrides from canonical environment variables."""
        return cls(
            locale=getenv(EnvVars.LOCALE, default="en-IN"),
            timezone=getenv(EnvVars.TIMEZONE, default="Asia/Kolkata"),
            currency=getenv(EnvVars.CURRENCY, default="INR"),
            country_code=getenv(EnvVars.COUNTRY, default="IN"),
        )

    def instruction(self) -> str:
        return (
            "Use Indian regional conventions where the website asks for them: "
            f"country={self.country_code}, locale={self.locale}, timezone={self.timezone}, "
            f"currency={self.currency}. Never invent an Indian address, identity, tax ID, "
            "phone number, OTP, or other personal value; use the user's supplied data."
        )


DEFAULT_INDIA_RUNTIME = IndiaRuntimeConfig.from_environment()
