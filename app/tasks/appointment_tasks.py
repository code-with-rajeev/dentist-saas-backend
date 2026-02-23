# ============================================================
# STUBBED — POST-MVP
# This module is not active in MVP.
# Implementation required before enabling:
#   - Celery worker running (see celery_app.py)
#   - Redis instance available
#   - Auto no-show detection requires scheduled beat task
# ============================================================

import logging

logger = logging.getLogger(__name__)


# @celery_app.task
def detect_no_shows() -> None:
    """
    POST-MVP: Automatically mark appointments as no-show
    if patient hasn't checked in X minutes after scheduled time.
    Triggered by Celery Beat on a scheduled interval.
    """
    logger.info("STUB: detect_no_shows task called — not active in MVP")


# @celery_app.task
def send_appointment_reminder(appointment_id: str) -> None:
    """
    POST-MVP: Send WhatsApp appointment reminder to patient
    24 hours before scheduled appointment.
    """
    logger.info(
        "STUB: send_appointment_reminder for %s — not active in MVP", appointment_id
    )
