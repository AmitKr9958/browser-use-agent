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
    """Deterministic tab selector; provide exactly one selector field."""

    index: int | None = None
    target_id: str | None = None
    title: str | None = None
    url: str | None = None
    title_contains: str | None = None
    url_contains: str | None = None

    def validate(self) -> None:
        fields = [
            self.index is not None,
            self.target_id is not None,
            self.title is not None,
            self.url is not None,
            self.title_contains is not None,
            self.url_contains is not None,
        ]
        if sum(fields) != 1:
            raise ValueError("TabSelector requires exactly one selector field")
