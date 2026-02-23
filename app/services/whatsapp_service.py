# ============================================================
# STUBBED — POST-MVP
# This module is not active in MVP.
# Implementation required before enabling:
#   - Meta Cloud API or Twilio credentials in .env
#   - WHATSAPP_API_URL, WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID
#   - WhatsApp webhook handler for inbound messages
# ============================================================

import logging

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Stub WhatsApp service — all methods return mock success in MVP."""

    async def send_consultation_report(
        self, phone: str, patient_name: str, pdf_path: str
    ) -> dict:
        """POST-MVP: Send PDF report to patient via WhatsApp."""
        logger.info("STUB: WhatsApp send_consultation_report called for %s", phone)
        return {"success": True, "message": "STUB: WhatsApp send not active in MVP"}

    async def send_appointment_reminder(
        self, phone: str, patient_name: str, appointment_date: str, time_slot: str
    ) -> dict:
        """POST-MVP: Send appointment reminder to patient."""
        logger.info("STUB: WhatsApp send_appointment_reminder called for %s", phone)
        return {"success": True, "message": "STUB: WhatsApp send not active in MVP"}

    async def send_follow_up_reminder(
        self, phone: str, patient_name: str, follow_up_date: str
    ) -> dict:
        """POST-MVP: Send follow-up reminder to patient."""
        logger.info("STUB: WhatsApp send_follow_up_reminder called for %s", phone)
        return {"success": True, "message": "STUB: WhatsApp send not active in MVP"}


whatsapp_service = WhatsAppService()
