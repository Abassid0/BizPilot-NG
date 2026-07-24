"""
app/services/payments/paystack.py
----------------------------------
All Paystack API interactions for BizPilot NG.

Handles:
  - Initialising subscription transactions
  - Verifying payments via webhook
  - Fetching subscription status
  - Cancelling subscriptions
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Optional

import httpx
from loguru import logger

from app.core.config import settings
from app.core.constants import SubscriptionTier


PAYSTACK_BASE = "https://api.paystack.co"

HEADERS = {
    "Authorization": f"Bearer {settings.paystack_secret_key}",
    "Content-Type": "application/json",
}


# ── Transaction Initialisation ───────────────────────────────────────────────

async def initialize_subscription(
    email: str,
    plan_code: str,
    telegram_id: int,
    tier: SubscriptionTier,
) -> Optional[dict]:
    """
    Create a Paystack transaction for a subscription plan.

    Returns:
        {
            "authorization_url": "https://checkout.paystack.com/...",
            "reference": "txn_ref_string",
        }
    or None on failure.
    """
    if tier == SubscriptionTier.PRO:
        amount_kobo = settings.pro_price_kobo
    else:
        amount_kobo = settings.business_price_kobo

    payload = {
        "email":    email,
        "amount":   amount_kobo,
        "plan":     plan_code,
        "metadata": {
            "telegram_id": str(telegram_id),
            "tier":        tier,
            "custom_fields": [
                {
                    "display_name": "Telegram ID",
                    "variable_name": "telegram_id",
                    "value": str(telegram_id),
                }
            ],
        },
        "callback_url": f"{settings.webhook_base_url}/payment/success",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{PAYSTACK_BASE}/transaction/initialize",
                headers=HEADERS,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        if data.get("status"):
            return {
                "authorization_url": data["data"]["authorization_url"],
                "reference":         data["data"]["reference"],
                "access_code":       data["data"]["access_code"],
            }
        logger.warning(f"Paystack init failed: {data.get('message')}")
        return None

    except httpx.HTTPError as e:
        logger.error(f"Paystack HTTP error during init: {e}")
        return None


# ── Payment Verification ─────────────────────────────────────────────────────

async def verify_transaction(reference: str) -> Optional[dict]:
    """
    Verify a transaction by reference after callback.

    Returns the full Paystack transaction data dict or None.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{PAYSTACK_BASE}/transaction/verify/{reference}",
                headers=HEADERS,
            )
            response.raise_for_status()
            data = response.json()

        if data.get("status") and data["data"]["status"] == "success":
            return data["data"]

        logger.warning(f"Transaction {reference} not successful: {data}")
        return None

    except httpx.HTTPError as e:
        logger.error(f"Paystack verify error: {e}")
        return None


def verify_webhook_signature(payload_bytes: bytes, signature: str) -> bool:
    """
    Verify that a webhook event genuinely came from Paystack.
    Paystack signs payloads with HMAC-SHA512 using your secret key.
    """
    if not settings.paystack_webhook_secret:
        logger.warning("PAYSTACK_WEBHOOK_SECRET not set — skipping signature verification")
        return True  # Allow in dev; enforce in production

    expected = hmac.new(
        key=settings.paystack_secret_key.encode("utf-8"),
        msg=payload_bytes,
        digestmod=hashlib.sha512,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


# ── Subscription Management ──────────────────────────────────────────────────

async def fetch_subscription(subscription_code: str) -> Optional[dict]:
    """Fetch a Paystack subscription object by its code."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{PAYSTACK_BASE}/subscription/{subscription_code}",
                headers=HEADERS,
            )
            response.raise_for_status()
            data = response.json()
        return data["data"] if data.get("status") else None
    except httpx.HTTPError as e:
        logger.error(f"fetch_subscription error: {e}")
        return None


async def cancel_subscription(
    subscription_code: str,
    email_token: str,
) -> bool:
    """
    Cancel a Paystack subscription.
    Requires the subscription code AND the email token from the subscription object.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{PAYSTACK_BASE}/subscription/disable",
                headers=HEADERS,
                json={
                    "code":  subscription_code,
                    "token": email_token,
                },
            )
            response.raise_for_status()
            data = response.json()
        return data.get("status", False)
    except httpx.HTTPError as e:
        logger.error(f"cancel_subscription error: {e}")
        return False


# ── Helpers ──────────────────────────────────────────────────────────────────

def kobo_to_naira(kobo: int) -> float:
    """Convert Paystack kobo amount to Naira."""
    return kobo / 100


def naira_to_kobo(naira: float) -> int:
    """Convert Naira amount to kobo for Paystack."""
    return int(naira * 100)


def format_naira(amount_naira: float) -> str:
    """Format a Naira amount as ₦1,234,567.00"""
    return f"₦{amount_naira:,.2f}"


def get_plan_code(tier: SubscriptionTier) -> Optional[str]:
    """Return the correct Paystack plan code for a subscription tier."""
    plans = {
        SubscriptionTier.PRO:       settings.paystack_pro_plan_code,
        SubscriptionTier.BUSINESS:  settings.paystack_commander_plan_code,
        SubscriptionTier.COMMANDER: settings.paystack_commander_plan_code,
    }
    return plans.get(tier)
