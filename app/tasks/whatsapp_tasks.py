# ============================================================
# STUBBED — POST-MVP
# This module is not active in MVP.
# Implementation required before enabling:
#   - Celery worker running (see celery_app.py)
#   - WhatsApp integration active (see whatsapp_service.py)
# ============================================================

import logging

logger = logging.getLogger(__name__)


# @celery_app.task
def send_consultation_report_whatsapp(consultation_id: str, phone: str) -> None:
    """
    POST-MVP: Send PDF consultation report to patient via WhatsApp.
    Triggered after consultation is submitted and PDF is generated.
    """
    logger.info(
        "STUB: send_consultation_report_whatsapp for %s — not active in MVP",
        consultation_id,
    )


# @celery_app.task
def send_follow_up_reminder_whatsapp(follow_up_id: str) -> None:
    """
    POST-MVP: Send follow-up reminder to patient via WhatsApp
    on the scheduled follow-up date.
    """
    logger.info(
        "STUB: send_follow_up_reminder_whatsapp for %s — not active in MVP", follow_up_id
    )
