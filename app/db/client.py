"""
app/db/client.py
----------------
Supabase client initialisation and all database operations.
One file owns all DB logic — no raw SQL scattered across the codebase.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from loguru import logger
from supabase import create_client, Client
from app.core.config import settings
from app.core.constants import SubscriptionTier, DocType, OutputFormat


# ── Singleton Supabase Client ───────────────────────────────────────────────

_supabase: Optional[Client] = None


def get_supabase() -> Client:
    """Service-role client — bypasses RLS for server-side operations."""
    global _supabase
    if _supabase is None:
        _supabase = create_client(settings.supabase_url, settings.supabase_service_key)
    return _supabase


class _LazySupabase:
    """Proxy that defers Supabase connection until first use."""
    def __getattr__(self, name: str) -> Any:
        return getattr(get_supabase(), name)


supabase: Client = _LazySupabase()  # type: ignore[assignment]


# ── User Operations ─────────────────────────────────────────────────────────

async def get_user_by_telegram_id(telegram_id: int) -> Optional[dict]:
    """Fetch user record by Telegram user ID."""
    try:
        result = supabase.table("users").select("*").eq(
            "telegram_id", telegram_id
        ).single().execute()
        return result.data
    except Exception:
        return None


async def create_user(
    telegram_id: int,
    full_name: str,
    username: Optional[str] = None,
) -> dict:
    """Create a new user with free tier defaults."""
    user = {
        "id":              str(uuid.uuid4()),
        "telegram_id":     telegram_id,
        "full_name":       full_name,
        "username":        username,
        "subscription":    SubscriptionTier.FREE,
        "docs_used":       0,
        "docs_limit":      settings.free_monthly_limit,
        "sub_expires_at":  None,
        "created_at":      datetime.now(timezone.utc).isoformat(),
    }
    result = supabase.table("users").insert(user).execute()
    return result.data[0]


async def update_user_profile(
    telegram_id: int,
    updates: dict,
) -> Optional[dict]:
    """Update any user fields by telegram_id."""
    try:
        result = supabase.table("users").update(updates).eq(
            "telegram_id", telegram_id
        ).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"update_user_profile error: {e}")
        return None


async def get_or_create_user(
    telegram_id: int,
    full_name: str,
    username: Optional[str] = None,
) -> tuple[dict, bool]:
    """
    Returns (user, is_new).
    is_new=True means we just created them — trigger onboarding.
    """
    user = await get_user_by_telegram_id(telegram_id)
    if user:
        return user, False
    user = await create_user(telegram_id, full_name, username)
    return user, True


async def increment_doc_count(telegram_id: int) -> None:
    """Increment the monthly document counter for a user."""
    try:
        supabase.rpc("increment_docs_used", {"p_telegram_id": telegram_id}).execute()
    except Exception as e:
        logger.error(f"increment_doc_count error: {e}")


async def check_usage_limit(telegram_id: int) -> tuple[bool, int, int]:
    """
    Returns (can_generate, used, limit).
    can_generate=False means the user has hit their monthly cap.
    """
    user = await get_user_by_telegram_id(telegram_id)
    if not user:
        return False, 0, 0
    used  = user.get("docs_used", 0)
    limit = user.get("docs_limit", settings.free_monthly_limit)
    return used < limit, used, limit


# ── Document Operations ─────────────────────────────────────────────────────

async def save_document(
    user_id: str,
    doc_type: DocType,
    input_data: dict,
    output_text: str,
    file_url: Optional[str] = None,
    output_format: OutputFormat = OutputFormat.TEXT,
) -> dict:
    """Persist a generated document to the database."""
    doc = {
        "id":            str(uuid.uuid4()),
        "user_id":       user_id,
        "doc_type":      doc_type,
        "input_data":    input_data,
        "output_text":   output_text,
        "file_url":      file_url,
        "output_format": output_format,
        "created_at":    datetime.now(timezone.utc).isoformat(),
    }
    result = supabase.table("documents").insert(doc).execute()
    return result.data[0]


async def get_user_documents(
    user_id: str,
    limit: int = 10,
) -> list[dict]:
    """Fetch recent documents for a user."""
    result = (
        supabase.table("documents")
        .select("id, doc_type, output_format, file_url, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


# ── Payment Operations ──────────────────────────────────────────────────────

async def create_payment_record(
    user_id: str,
    paystack_ref: str,
    amount_kobo: int,
    plan: str,
    status: str = "pending",
) -> dict:
    """Record a payment initiation."""
    payment = {
        "id":           str(uuid.uuid4()),
        "user_id":      user_id,
        "paystack_ref": paystack_ref,
        "amount_kobo":  amount_kobo,
        "plan":         plan,
        "status":       status,
        "created_at":   datetime.now(timezone.utc).isoformat(),
    }
    result = supabase.table("payments").insert(payment).execute()
    return result.data[0]


async def confirm_payment(
    paystack_ref: str,
    amount_kobo: int,
) -> Optional[dict]:
    """
    Mark a payment as successful and upgrade the user's subscription.
    Called by the Paystack webhook handler.
    """
    try:
        # Update payment status
        result = (
            supabase.table("payments")
            .update({"status": "success", "paid_at": datetime.now(timezone.utc).isoformat()})
            .eq("paystack_ref", paystack_ref)
            .execute()
        )
        if not result.data:
            return None

        payment = result.data[0]

        # Determine subscription tier from amount
        if amount_kobo >= settings.commander_price_kobo:
            tier   = SubscriptionTier.COMMANDER
            limit  = settings.commander_monthly_limit
        else:
            tier   = SubscriptionTier.PRO
            limit  = settings.pro_monthly_limit

        # Calculate subscription expiry (30 days from now)
        from datetime import timedelta
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

        # Upgrade user
        await supabase.table("users").update({
            "subscription":   tier,
            "docs_limit":     limit,
            "sub_expires_at": expires_at,
        }).eq("id", payment["user_id"]).execute()

        return payment
    except Exception as e:
        logger.error(f"confirm_payment error: {e}")
        return None


async def get_payment_by_ref(paystack_ref: str) -> Optional[dict]:
    """Fetch a payment record by Paystack reference."""
    try:
        result = (
            supabase.table("payments")
            .select("*, users(*)")
            .eq("paystack_ref", paystack_ref)
            .single()
            .execute()
        )
        return result.data
    except Exception:
        return None


# ── Business Profile ────────────────────────────────────────────────────────

async def save_business_profile(
    telegram_id: int,
    profile: dict,
) -> Optional[dict]:
    """
    Store the user's business profile.
    profile keys: business_name, business_type, industry,
                  cac_number, tin_number, bank_name,
                  account_number, account_name, logo_url
    """
    return await update_user_profile(telegram_id, {"business_profile": profile})


async def get_business_profile(telegram_id: int) -> dict:
    """Return the business profile sub-object, or empty dict if not set."""
    user = await get_user_by_telegram_id(telegram_id)
    if not user:
        return {}
    return user.get("business_profile") or {}
