# Standard library
import logging

# Third-party
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

# Internal — core
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.error_handlers import (
    app_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import configure_logging

# Internal — routers
from app.api.router import router

# Configure logging before anything else runs
configure_logging()

logger = logging.getLogger(__name__)

# ============================================================
# FastAPI application
# ============================================================
app = FastAPI(
    title="Dentist AI SaaS API",
    description="Production-ready backend for dental clinic management",
    version="1.0.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    openapi_url="/openapi.json" if settings.is_development else None,
)

# ============================================================
# CORS Middleware — env-aware
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,       # ["*"] in dev, restricted in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Global Exception Handlers
# ============================================================
app.add_exception_handler(AppException, app_exception_handler)          # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(StarletteHTTPException, http_exception_handler)        # type: ignore[arg-type]
app.add_exception_handler(Exception, unhandled_exception_handler)

# ============================================================
# Routers
# ============================================================
app.include_router(router)

# Routers — registered as each phase is completed
from app.api.v1.auth import router as auth_router
from app.api.v1.clinic import router as clinic_router
from app.api.v1.patients import router as patients_router
from app.api.v1.appointments import router as appointments_router
from app.api.v1.consultations import router as consultations_router
from app.api.v1.analytics import router as analytics_router
app.include_router(auth_router, prefix="/api/v1")
app.include_router(clinic_router, prefix="/api/v1")
app.include_router(patients_router, prefix="/api/v1")
app.include_router(appointments_router, prefix="/api/v1")
app.include_router(consultations_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")

# Phase 7+ routers (uncomment as each phase is built):
# from app.api.v1.appointments import router as appointments_router
# from app.api.v1.consultations import router as consultations_router
# from app.api.v1.analytics import router as analytics_router
# app.include_router(appointments_router, prefix="/api/v1")
# app.include_router(consultations_router, prefix="/api/v1")
# app.include_router(analytics_router, prefix="/api/v1")


# ============================================================
# Startup / Shutdown Events
# ============================================================
@app.on_event("startup")
async def on_startup() -> None:
    logger.info(
        "🚀 Dentist AI SaaS starting | env=%s | debug=%s",
        settings.APP_ENV,
        settings.APP_DEBUG,
    )
    # Verify DB connectivity at startup
    try:
        from app.database.session import engine
        from sqlalchemy import text

        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection verified")
    except Exception as exc:
        logger.error("❌ Database connection FAILED at startup: %s", exc)
        raise


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("🛑 Dentist AI SaaS shutting down")
    from app.database.session import engine
    await engine.dispose()
