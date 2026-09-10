"""Deterministic browser-tab discovery and selection."""

from .manager import TabManager
from .models import TabRecord, TabSelector

__all__ = ["TabManager", "TabRecord", "TabSelector"]
