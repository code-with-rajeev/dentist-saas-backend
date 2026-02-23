# Standard library
import logging

# Third-party
from fastapi import APIRouter

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", tags=["health"])
async def health_check() -> dict:
    """
    Health check endpoint.
    Returns 200 OK when the app is running.
    Used by load balancers, Docker health checks, and monitoring tools.
    """
    return {
        "success": True,
        "message": "Service is healthy",
        "data": {"status": "ok"},
    }
