"""Unified BrowserSession lifecycle management."""

from __future__ import annotations

import logging
from typing import Any

from browser_agent.utils import await_if_needed
from .harness import start_browser_harness_session, stop_browser_harness_session

logger = logging.getLogger(__name__)


class BrowserSessionManager:
    """Own a BrowserSession only when this manager created it."""

    def __init__(self, session: Any | None = None) -> None:
        self.session = session
        self.owns_session = session is None

    async def __aenter__(self) -> Any:
        if self.owns_session:
            self.session = await start_browser_harness_session()
            logger.debug("Started new browser harness session")
        else:
            await self._ensure_started()
        return self.session

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        if self.owns_session and self.session is not None:
            try:
                await stop_browser_harness_session(self.session)
                logger.debug("Stopped owned browser harness session")
            except Exception as exc:
                logger.warning("Error stopping browser session: %s", exc, exc_info=True)

    async def _ensure_started(self) -> None:
        if self.session is None:
            raise RuntimeError("Browser session is not initialized")
        cdp_client = getattr(self.session, "cdp_client", None)
        cdp_root = getattr(self.session, "_cdp_client_root", None)
        if cdp_client is not None or cdp_root is not None:
            return
        start = getattr(self.session, "start", None)
        if callable(start):
            await await_if_needed(start())
