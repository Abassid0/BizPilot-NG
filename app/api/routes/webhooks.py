"""
app/api/routes/webhooks.py
---------------------------
Two critical webhook endpoints:

  POST /webhook/telegram/{secret}
      Receives all Telegram updates and passes them to python-telegram-bot.

  POST /webhook/paystack
      Receives Paystack payment events, verifies signature,
      and upgrades the user's subscription.
"""

from __future__ import annotations

import hashlib
import hmac
import json

from fastapi import APIRouter, Request, Response, HTTPException, Depends
from loguru import logger
from telegram import Update

from app.core.config import settings
from app.db.client import confirm_payment, get_payment_by_ref, get_user_by_telegram_id
from app.services.payments.paystack import verify_webhook_signature, verify_transaction

router = APIRouter(tags=["webhooks"])


# ── Telegram Webhook ─────────────────────────────────────────────────────────

@router.post("/webhook/telegram/{secret}")
async def telegram_webhook(secret: str, request: Request) -> Response:
    """
    Receives Telegram updates via webhook.
    The {secret} path param acts as a shared secret to prevent
    anyone else from posting fake updates.
    """
    if secret != settings.telegram_webhook_secret:
        logger.warning(f"Invalid webhook secret received: {secret[:8]}...")
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Get the bot application from app state
    bot_app = request.app.state.bot_app

    update = Update.de_json(body, bot_app.bot)
    await bot_app.process_update(update)

    return Response(status_code=200)


# ── Paystack Webhook ──────────────────────────────────────────────────────────

@router.post("/webhook/paystack")
async def paystack_webhook(request: Request) -> Response:
    """
    Receives Paystack payment events.

    Paystack sends events for:
      - charge.success  → subscription payment succeeded
      - subscription.disable → subscription cancelled
      - invoice.payment_failed → renewal failed

    We only act on charge.success for now.
    """
    body_bytes = await request.body()
    signature  = request.headers.get("x-paystack-signature", "")

    # Verify the request genuinely came from Paystack
    if not verify_webhook_signature(body_bytes, signature):
        logger.warning("Paystack webhook signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        event = json.loads(body_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = event.get("event")
    data       = event.get("data", {})

    logger.info(f"Paystack webhook received: {event_type}")

    if event_type == "charge.success":
        await _handle_charge_success(data, request)

    elif event_type == "subscription.disable":
        await _handle_subscription_disabled(data, request)

    elif event_type == "invoice.payment_failed":
        logger.warning(f"Payment failed for subscription: {data.get('subscription', {}).get('subscription_code')}")

    # Always return 200 to Paystack — retries happen if we return 4xx/5xx
    return Response(status_code=200)


async def _handle_charge_success(data: dict, request: Request) -> None:
    """Process a successful charge and activate the user's subscription."""
    reference   = data.get("reference", "")
    amount_kobo = data.get("amount", 0)
    metadata    = data.get("metadata", {})
    telegram_id = metadata.get("telegram_id")
    customer    = data.get("customer", {})
    email       = customer.get("email", "")

    logger.info(f"Charge success: ref={reference} amount={amount_kobo} telegram_id={telegram_id}")

    # Verify with Paystack API (don't trust webhook data alone)
    verified = await verify_transaction(reference)
    if not verified:
        logger.error(f"Could not verify transaction {reference}")
        return

    # Update database
    payment = await confirm_payment(reference, amount_kobo)
    if not payment:
        logger.error(f"confirm_payment returned None for ref={reference}")
        return

    # Send Telegram confirmation to the user
    if telegram_id:
        try:
            bot_app = request.app.state.bot_app
            tier_label = "Pro Operator ⚡" if amount_kobo < settings.commander_price_kobo else "Business Commander 🏆"
            await bot_app.bot.send_message(
                chat_id=int(telegram_id),
                text=(
                    f"🎉 *Payment Confirmed!*\n\n"
                    f"Your *{tier_label}* subscription is now active.\n"
                    f"You now have unlimited document generation.\n\n"
                    f"Reference: `{reference}`\n\n"
                    f"Type /help to see all available commands."
                ),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram confirmation: {e}")


async def _handle_subscription_disabled(data: dict, request: Request) -> None:
    """Downgrade user to free tier when subscription is cancelled."""
    from app.db.client import supabase
    customer_code = data.get("customer", {}).get("customer_code")
    logger.info(f"Subscription disabled for customer: {customer_code}")

    # In a full implementation you'd look up the user by customer_code
    # For MVP, log and handle manually if needed
