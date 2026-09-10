"""Application layer for deterministic Browser Use + Browser Harness automation."""

from .agents import run_on_tab
from .tabs.errors import AmbiguousTabError, TabNotFoundError, TabVerificationError
from .tabs.manager import TabManager
from .tabs.models import TabRecord, TabSelector

__all__ = [
    "AmbiguousTabError",
    "TabManager",
    "TabNotFoundError",
    "TabRecord",
    "TabSelector",
    "TabVerificationError",
    "run_on_tab",
]
