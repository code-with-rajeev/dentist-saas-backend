# Standard library
from typing import Any, Generic, TypeVar

# Third-party
from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success envelope used across all routes."""
    success: bool = True
    message: str
    data: T | None = None


class PaginatedMeta(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response envelope."""
    success: bool = True
    message: str
    data: list[T]
    meta: PaginatedMeta
