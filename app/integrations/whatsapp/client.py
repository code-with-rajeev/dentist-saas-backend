# ============================================================
# STUBBED — POST-MVP
# This module is not active in MVP.
# Implementation required before enabling:
#   - WhatsApp provider chosen (Meta Cloud API or Twilio)
#   - WHATSAPP_API_URL, WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID in .env
# ============================================================

import logging

logger = logging.getLogger(__name__)


class WhatsAppClient:
    """
    POST-MVP: WhatsApp API client.
    Wraps the chosen provider (Meta Cloud API or Twilio).
    """

    async def send_text_message(self, phone: str, message: str) -> dict:
        """POST-MVP: Send plain text message."""
        logger.info("STUB: WhatsApp send_text_message to %s — not active in MVP", phone)
        return {"success": True, "message": "STUB"}

    async def send_document(self, phone: str, document_url: str, caption: str) -> dict:
        """POST-MVP: Send document (PDF report)."""
        logger.info("STUB: WhatsApp send_document to %s — not active in MVP", phone)
        return {"success": True, "message": "STUB"}

    async def send_template_message(
        self, phone: str, template_name: str, params: list
    ) -> dict:
        """POST-MVP: Send pre-approved WhatsApp template message."""
        logger.info(
            "STUB: WhatsApp send_template_message '%s' to %s — not active in MVP",
            template_name,
            phone,
        )
        return {"success": True, "message": "STUB"}


whatsapp_client = WhatsAppClient()
