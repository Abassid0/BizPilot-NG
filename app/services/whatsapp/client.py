"""
app/services/whatsapp/client.py
---------------------------------
WhatsApp Business API client for sending messages.

Uses the Meta Cloud API (v21.0+). Requires:
  - WHATSAPP_ACCESS_TOKEN (permanent system user token)
  - WHATSAPP_PHONE_NUMBER_ID (from Meta Business dashboard)

This is a scaffold — connect once Meta Business credentials are configured.
"""

from __future__ import annotations

from typing import Optional
import httpx
from loguru import logger

from app.core.config import settings

WA_API_BASE = "https://graph.facebook.com/v21.0"


def _is_configured() -> bool:
    return bool(settings.whatsapp_access_token and settings.whatsapp_phone_number_id)


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }


async def send_text_message(to: str, text: str) -> Optional[dict]:
    """
    Send a plain text message to a WhatsApp number.
    `to` should be in international format without + (e.g. '2348012345678').
    """
    if not _is_configured():
        logger.warning("WhatsApp not configured — skipping message send")
        return None

    url = f"{WA_API_BASE}/{settings.whatsapp_phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(url, json=payload, headers=_headers())
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"WhatsApp message sent to {to}")
            return data
        except httpx.HTTPStatusError as e:
            logger.error(f"WhatsApp API error {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"WhatsApp send error: {e}")
            return None


async def send_interactive_buttons(
    to: str,
    body_text: str,
    buttons: list[dict],
    header: str = "",
    footer: str = "",
) -> Optional[dict]:
    """
    Send an interactive button message (max 3 buttons).
    buttons: [{"id": "btn_1", "title": "Option A"}, ...]
    """
    if not _is_configured():
        return None

    url = f"{WA_API_BASE}/{settings.whatsapp_phone_number_id}/messages"

    action_buttons = [
        {"type": "reply", "reply": {"id": b["id"], "title": b["title"][:20]}}
        for b in buttons[:3]
    ]

    interactive: dict = {
        "type": "button",
        "body": {"text": body_text},
        "action": {"buttons": action_buttons},
    }
    if header:
        interactive["header"] = {"type": "text", "text": header}
    if footer:
        interactive["footer"] = {"text": footer}

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": interactive,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(url, json=payload, headers=_headers())
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"WhatsApp interactive send error: {e}")
            return None


async def send_template_message(
    to: str,
    template_name: str,
    language_code: str = "en",
    components: Optional[list] = None,
) -> Optional[dict]:
    """Send a pre-approved WhatsApp template message."""
    if not _is_configured():
        return None

    url = f"{WA_API_BASE}/{settings.whatsapp_phone_number_id}/messages"

    template: dict = {
        "name": template_name,
        "language": {"code": language_code},
    }
    if components:
        template["components"] = components

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": template,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(url, json=payload, headers=_headers())
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"WhatsApp template send error: {e}")
            return None


async def mark_message_read(message_id: str) -> None:
    """Mark a received message as read (blue ticks)."""
    if not _is_configured():
        return

    url = f"{WA_API_BASE}/{settings.whatsapp_phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            await client.post(url, json=payload, headers=_headers())
        except Exception as e:
            logger.debug(f"Mark read failed: {e}")
