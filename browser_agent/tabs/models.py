"""Stable data models used by the tab controller."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TabRecord:
    """A serializable snapshot of one browser tab."""

    index: int
    target_id: str
    title: str
    url: str


@dataclass(frozen=True, slots=True)
class TabSelector:
    """Deterministic tab selector; provide exactly one non-empty selector field."""

    index: int | None = None
    target_id: str | None = None
    title: str | None = None
    url: str | None = None
    title_contains: str | None = None
    url_contains: str | None = None

    def validate(self) -> None:
        provided = [
            ("index", self.index),
            ("target_id", self.target_id),
            ("title", self.title),
            ("url", self.url),
            ("title_contains", self.title_contains),
            ("url_contains", self.url_contains),
        ]
        selected = [(name, value) for name, value in provided if value is not None]
        if len(selected) != 1:
            raise ValueError("TabSelector requires exactly one selector field")
        name, value = selected[0]
        if name == "index":
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError("TabSelector index must be a non-negative integer")
            return
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"TabSelector {name} must not be empty")
