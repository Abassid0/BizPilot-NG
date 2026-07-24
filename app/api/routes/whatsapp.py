"""
app/api/routes/whatsapp.py
-----------------------------
WhatsApp Business API webhook handler.

Meta sends:
  - GET  /webhook/whatsapp  — Verification challenge (one-time setup)
  - POST /webhook/whatsapp  — Incoming messages, statuses, errors

This scaffold receives messages and routes them to the same AI pipeline
used by the Telegram bot. Activate by setting WHATSAPP_* env vars.
"""

from __future__ import annotations

import hashlib
import hmac

from fastapi import APIRouter, HTTPException, Query, Request
from loguru import logger

from app.core.config import settings
from app.db.client import get_or_create_user, get_business_profile
from app.services.whatsapp.client import (
    send_text_message,
    send_interactive_buttons,
    mark_message_read,
)

router = APIRouter(prefix="/webhook", tags=["whatsapp"])


@router.get("/whatsapp")
async def verify_webhook(
    mode: str = Query(alias="hub.mode", default=""),
    token: str = Query(alias="hub.verify_token", default=""),
    challenge: str = Query(alias="hub.challenge", default=""),
):
    """Meta webhook verification — returns the challenge if token matches."""
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        logger.info("WhatsApp webhook verified")
        return int(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp")
async def receive_webhook(request: Request):
    """Handle incoming WhatsApp messages."""
    body = await request.json()

    if settings.whatsapp_app_secret:
        signature = request.headers.get("X-Hub-Signature-256", "")
        raw_body = await request.body()
        expected = "sha256=" + hmac.new(
            settings.whatsapp_app_secret.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        entries = body.get("entry", [])
        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})

                if "statuses" in value:
                    continue

                messages = value.get("messages", [])
                contacts = value.get("contacts", [])

                for msg in messages:
                    await _handle_message(msg, contacts)

    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}")

    return {"status": "ok"}


async def _handle_message(msg: dict, contacts: list) -> None:
    """Route an incoming WhatsApp message."""
    msg_type = msg.get("type")
    sender = msg.get("from", "")
    msg_id = msg.get("id", "")

    contact_name = ""
    if contacts:
        profile = contacts[0].get("profile", {})
        contact_name = profile.get("name", "")

    await mark_message_read(msg_id)

    wa_id = int(sender) if sender.isdigit() else 0
    if wa_id == 0:
        return

    user, is_new = await get_or_create_user(
        telegram_id=wa_id,
        full_name=contact_name or "WhatsApp User",
        username=None,
    )

    if is_new:
        await send_text_message(
            sender,
            "Welcome to BizPilot NG! 🇳🇬\n\n"
            "I help Nigerian entrepreneurs with:\n"
            "📄 Invoices & Proposals\n"
            "💰 Expense Tracking\n"
            "📊 Financial Dashboards\n"
            "🧾 Tax Compliance\n\n"
            "Send me a message to get started!",
        )
        return

    if msg_type == "text":
        text = msg.get("text", {}).get("body", "").strip()
        if not text:
            return
        await _handle_text_message(sender, user, text)

    elif msg_type == "image":
        await send_text_message(
            sender,
            "Receipt scanning via WhatsApp is coming soon! "
            "For now, use the Telegram bot for OCR scanning.",
        )

    elif msg_type == "interactive":
        interactive = msg.get("interactive", {})
        button_reply = interactive.get("button_reply", {})
        button_id = button_reply.get("id", "")
        if button_id:
            await _handle_button(sender, user, button_id)

    else:
        await send_text_message(
            sender,
            "I can help with text messages right now. "
            "Type 'menu' to see what I can do!",
        )


async def _handle_text_message(sender: str, user: dict, text: str) -> None:
    """Process a text message from WhatsApp."""
    text_lower = text.lower().strip()

    if text_lower in ("menu", "help", "start", "hi", "hello"):
        await send_interactive_buttons(
            sender,
            "What would you like to do?",
            [
                {"id": "wa_expense", "title": "Log Expense"},
                {"id": "wa_dashboard", "title": "Dashboard"},
                {"id": "wa_documents", "title": "Documents"},
            ],
            header="BizPilot NG",
            footer="Type anything to ask a question",
        )
        return

    from app.services.ai.claude_client import parse_quick_expense
    parsed = await parse_quick_expense(text)
    if parsed and parsed.get("amount") and parsed.get("confidence", 0) > 0.6:
        from app.db.client import save_expense
        await save_expense(
            user_id=user["id"],
            amount=float(parsed["amount"]),
            description=parsed.get("description", text),
            category=parsed.get("category", "Miscellaneous"),
            vendor=parsed.get("vendor", ""),
            source="manual",
        )
        await send_text_message(
            sender,
            f"✅ Expense logged!\n\n"
            f"Amount: ₦{float(parsed['amount']):,.0f}\n"
            f"Category: {parsed.get('category', 'Miscellaneous')}\n"
            f"Description: {parsed.get('description', text)}",
        )
        return

    await send_text_message(
        sender,
        "I'm not sure what you mean. Type 'menu' to see what I can do, "
        "or type an expense like 'spent 5k on fuel' to log it quickly.",
    )


async def _handle_button(sender: str, user: dict, button_id: str) -> None:
    """Handle interactive button presses."""
    if button_id == "wa_expense":
        await send_text_message(
            sender,
            "To log an expense, just type it naturally:\n\n"
            "Examples:\n"
            "• spent 5000 on fuel\n"
            "• uber to VI 3500\n"
            "• bought rice 25000\n"
            "• DSTV subscription 21000",
        )

    elif button_id == "wa_dashboard":
        from app.db.client import get_expense_summary, get_income_summary
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        expenses = await get_expense_summary(user["id"], year=now.year, month=now.month)
        income = await get_income_summary(user["id"], year=now.year, month=now.month)

        profit = income["total"] - expenses["total"]
        label = "Profit" if profit >= 0 else "Loss"

        text = (
            f"📊 *{now.strftime('%B %Y')}*\n\n"
            f"Income: ₦{income['total']:,.0f}\n"
            f"Expenses: ₦{expenses['total']:,.0f}\n"
            f"Net {label}: ₦{abs(profit):,.0f}\n\n"
            f"Expenses: {expenses['count']} entries\n"
            f"Income: {income['count']} entries"
        )
        await send_text_message(sender, text)

    elif button_id == "wa_documents":
        await send_text_message(
            sender,
            "Document generation is available on our Telegram bot for now.\n\n"
            "Full WhatsApp document support coming soon!",
        )
