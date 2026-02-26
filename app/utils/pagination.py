"""Pagination helper used across all list endpoints."""

# Standard library
import math
from dataclasses import dataclass
from typing import Any


@dataclass
class PaginatedResult:
    items: list[Any]
    total: int
    page: int
    per_page: int

    @property
    def pages(self) -> int:
        if self.per_page == 0:
            return 0
        return math.ceil(self.total / self.per_page)

    def to_meta(self) -> dict:
        return {
            "total": self.total,
            "page": self.page,
            "per_page": self.per_page,
            "pages": self.pages,
        }


def paginate(*, page: int = 1, per_page: int = 20) -> tuple[int, int]:
    """
    Returns (offset, limit) for a SQLAlchemy query.
    Clamps page to ≥1 and per_page to 1–100.
    """
    page = max(1, page)
    per_page = min(max(1, per_page), 100)
    offset = (page - 1) * per_page
    return offset, per_page
