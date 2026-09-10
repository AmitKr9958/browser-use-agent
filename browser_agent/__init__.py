"""Application layer for deterministic Browser Use + Browser Harness automation."""

from .tabs.manager import TabManager
from .tabs.models import TabRecord, TabSelector

__all__ = ["TabManager", "TabRecord", "TabSelector"]
