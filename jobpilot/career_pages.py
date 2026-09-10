"""Career-page records and fast lookup for a user's company database."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class CareerPage:
    company: str
    url: str
    ats: str | None = None
    application_url: str | None = None


class CareerPageRegistry:
    """In-memory index; adapters can load the same records from any database."""

    def __init__(self, pages: list[CareerPage] | None = None) -> None:
        self._pages = pages or []

    def add(self, page: CareerPage) -> None:
        self._pages.append(page)

    def match_url(self, url: str) -> CareerPage | None:
        host = urlparse(url).netloc.casefold()
        path = urlparse(url).path.casefold()
        candidates = [p for p in self._pages if urlparse(p.url).netloc.casefold() == host]
        if not candidates:
            return None
        for page in candidates:
            if urlparse(page.url).path.casefold() == path:
                return page
        return candidates[0]

    def all(self) -> tuple[CareerPage, ...]:
        return tuple(self._pages)
