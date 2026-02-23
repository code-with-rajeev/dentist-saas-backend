# ============================================================
# STUBBED — POST-MVP
# This module is not active in MVP.
# Implementation required before enabling:
#   - Redis instance running (REDIS_URL in .env)
#   - Celery worker process: celery -A app.tasks.celery_app worker
#   - Uncomment the Celery app initialization below
# ============================================================

# from celery import Celery
# from app.core.config import settings
#
# celery_app = Celery(
#     "dentist_saas",
#     broker=settings.CELERY_BROKER_URL,
#     backend=settings.CELERY_RESULT_BACKEND,
# )
#
# celery_app.conf.update(
#     task_serializer="json",
#     accept_content=["json"],
#     result_serializer="json",
#     timezone="UTC",
#     enable_utc=True,
# )

# Placeholder — prevents import errors in MVP
celery_app = None
