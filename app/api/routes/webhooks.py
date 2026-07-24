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
from app.db.client import confirm_payment, get_payment_by_ref, get_user_by_telegram_id, downgrade_user_to_free
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
        await _handle_payment_failed(data, request)

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

    tier_label = "Pro Operator" if amount_kobo < settings.commander_price_kobo else "Business Commander"

    if email:
        from app.services.payments.paystack import format_naira, kobo_to_naira
        from app.services.payments.email import send_payment_confirmation
        await send_payment_confirmation(
            to=email,
            name=email.split("@")[0],
            plan_name=tier_label,
            amount=format_naira(kobo_to_naira(amount_kobo)),
            reference=reference,
        )

    if telegram_id:
        try:
            bot_app = request.app.state.bot_app
            await bot_app.bot.send_message(
                chat_id=int(telegram_id),
                text=(
                    f"*Payment Confirmed!*\n\n"
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
    customer_code = data.get("customer", {}).get("customer_code")
    email = data.get("customer", {}).get("email", "")
    logger.info(f"Subscription disabled for customer: {customer_code}")

    metadata = data.get("metadata", {})
    telegram_id = metadata.get("telegram_id")

    if not telegram_id:
        subscription = data.get("subscription", {})
        sub_meta = subscription.get("metadata", {})
        telegram_id = sub_meta.get("telegram_id")

    if not telegram_id:
        logger.warning(f"No telegram_id in subscription.disable event for {customer_code}")
        return

    telegram_id = int(telegram_id)
    user = await get_user_by_telegram_id(telegram_id)
    if not user:
        logger.warning(f"User not found for telegram_id={telegram_id} during subscription disable")
        return

    await downgrade_user_to_free(telegram_id)
    logger.info(f"User {telegram_id} downgraded to free tier after subscription cancellation")

    try:
        bot_app = request.app.state.bot_app
        await bot_app.bot.send_message(
            chat_id=telegram_id,
            text=(
                "Your subscription has been cancelled.\n\n"
                "You've been moved to the *Starter (Free)* plan with 5 documents per month.\n\n"
                "Type /upgrade anytime to resubscribe."
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Failed to notify user {telegram_id} of cancellation: {e}")


async def _handle_payment_failed(data: dict, request: Request) -> None:
    """Notify user when a subscription renewal payment fails."""
    subscription = data.get("subscription", {})
    sub_code = subscription.get("subscription_code", "unknown")
    metadata = data.get("metadata", {}) or subscription.get("metadata", {})
    telegram_id = metadata.get("telegram_id")

    logger.warning(f"Payment failed for subscription: {sub_code}, telegram_id={telegram_id}")

    if not telegram_id:
        return

    try:
        bot_app = request.app.state.bot_app
        await bot_app.bot.send_message(
            chat_id=int(telegram_id),
            text=(
                "Your subscription renewal payment failed.\n\n"
                "Please update your payment method to keep your plan active. "
                "Your subscription will be cancelled if the next retry also fails.\n\n"
                "Type /upgrade to set up a new payment."
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Failed to notify user {telegram_id} of payment failure: {e}")
