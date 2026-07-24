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


async def downgrade_user_to_free(telegram_id: int) -> None:
    """Reset a user's subscription to free tier after cancellation."""
    try:
        supabase.table("users").update({
            "subscription":   SubscriptionTier.FREE,
            "docs_limit":     settings.free_monthly_limit,
            "sub_expires_at": None,
        }).eq("telegram_id", telegram_id).execute()
    except Exception as e:
        logger.error(f"downgrade_user_to_free error: {e}")


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


async def check_and_send_usage_warning(telegram_id: int) -> None:
    """Send an email warning when user hits 80% of their doc limit."""
    user = await get_user_by_telegram_id(telegram_id)
    if not user:
        return
    used = user.get("docs_used", 0)
    limit = user.get("docs_limit", settings.free_monthly_limit)
    email = user.get("email")
    if not email or limit >= 999999:
        return
    if used == int(limit * 0.8):
        from app.services.payments.email import send_usage_warning
        await send_usage_warning(email, user.get("full_name", "there"), used, limit)


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
        if amount_kobo >= settings.business_price_kobo:
            tier   = SubscriptionTier.BUSINESS
            limit  = settings.business_monthly_limit
        else:
            tier   = SubscriptionTier.PRO
            limit  = settings.pro_monthly_limit

        # Calculate subscription expiry (30 days from now)
        from datetime import timedelta
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

        supabase.table("users").update({
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


# ── Expense Operations ─────────────────────────────────────────────────────

async def save_expense(
    user_id: str,
    amount: float,
    description: str,
    category: str = "Miscellaneous",
    vendor: str = "",
    expense_date: Optional[str] = None,
    source: str = "manual",
    receipt_url: Optional[str] = None,
    ocr_raw: Optional[dict] = None,
) -> Optional[dict]:
    """Save an expense record."""
    import uuid as _uuid
    from datetime import date
    expense = {
        "id":           str(_uuid.uuid4()),
        "user_id":      user_id,
        "amount":       amount,
        "description":  description,
        "category":     category,
        "vendor":       vendor,
        "expense_date": expense_date or date.today().isoformat(),
        "source":       source,
        "receipt_url":  receipt_url,
        "ocr_raw":      ocr_raw or {},
        "created_at":   datetime.now(timezone.utc).isoformat(),
    }
    try:
        result = supabase.table("expenses").insert(expense).execute()
        return result.data[0]
    except Exception as e:
        logger.error(f"save_expense error: {e}")
        return None


async def get_user_expenses(
    user_id: str,
    limit: int = 50,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> list[dict]:
    """Fetch expenses, optionally filtered by year/month."""
    try:
        query = (
            supabase.table("expenses")
            .select("*")
            .eq("user_id", user_id)
            .order("expense_date", desc=True)
        )
        if year and month:
            start = f"{year}-{month:02d}-01"
            if month == 12:
                end = f"{year + 1}-01-01"
            else:
                end = f"{year}-{month + 1:02d}-01"
            query = query.gte("expense_date", start).lt("expense_date", end)
        query = query.limit(limit)
        result = query.execute()
        return result.data or []
    except Exception as e:
        logger.error(f"get_user_expenses error: {e}")
        return []


async def get_expense_summary(
    user_id: str,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> dict:
    """Get expense totals grouped by category for a given period."""
    expenses = await get_user_expenses(user_id, limit=500, year=year, month=month)
    by_category: dict[str, float] = {}
    total = 0.0
    for exp in expenses:
        cat = exp.get("category", "Miscellaneous")
        amt = float(exp.get("amount", 0))
        by_category[cat] = by_category.get(cat, 0) + amt
        total += amt
    return {
        "total": total,
        "count": len(expenses),
        "by_category": dict(sorted(by_category.items(), key=lambda x: -x[1])),
    }


# ── Income Operations ──────────────────────────────────────────────────────

async def save_income(
    user_id: str,
    amount: float,
    description: str,
    client_name: str = "",
    category: str = "Services",
    income_date: Optional[str] = None,
    invoice_id: Optional[str] = None,
) -> Optional[dict]:
    """Save an income record."""
    import uuid as _uuid
    from datetime import date
    record = {
        "id":          str(_uuid.uuid4()),
        "user_id":     user_id,
        "amount":      amount,
        "description": description,
        "client_name": client_name,
        "category":    category,
        "income_date": income_date or date.today().isoformat(),
        "invoice_id":  invoice_id,
        "created_at":  datetime.now(timezone.utc).isoformat(),
    }
    try:
        result = supabase.table("income").insert(record).execute()
        return result.data[0]
    except Exception as e:
        logger.error(f"save_income error: {e}")
        return None


async def get_income_summary(
    user_id: str,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> dict:
    """Get income totals for a given period."""
    try:
        query = (
            supabase.table("income")
            .select("*")
            .eq("user_id", user_id)
            .order("income_date", desc=True)
        )
        if year and month:
            start = f"{year}-{month:02d}-01"
            if month == 12:
                end = f"{year + 1}-01-01"
            else:
                end = f"{year}-{month + 1:02d}-01"
            query = query.gte("income_date", start).lt("income_date", end)
        query = query.limit(500)
        result = query.execute()
        records = result.data or []
    except Exception as e:
        logger.error(f"get_income_summary error: {e}")
        records = []

    by_category: dict[str, float] = {}
    total = 0.0
    for rec in records:
        cat = rec.get("category", "Services")
        amt = float(rec.get("amount", 0))
        by_category[cat] = by_category.get(cat, 0) + amt
        total += amt
    return {
        "total": total,
        "count": len(records),
        "by_category": dict(sorted(by_category.items(), key=lambda x: -x[1])),
    }


# ── Tax Record Operations ─────────────────────────────────────────────────

async def save_tax_record(
    user_id: str,
    tax_type: str,
    period_start: str,
    period_end: str,
    gross_amount: float,
    tax_amount: float,
    due_date: Optional[str] = None,
    details: Optional[dict] = None,
) -> Optional[dict]:
    """Save a calculated tax record."""
    import uuid as _uuid
    record = {
        "id":           str(_uuid.uuid4()),
        "user_id":      user_id,
        "tax_type":     tax_type,
        "period_start": period_start,
        "period_end":   period_end,
        "gross_amount": gross_amount,
        "tax_amount":   tax_amount,
        "due_date":     due_date,
        "details":      details or {},
        "created_at":   datetime.now(timezone.utc).isoformat(),
    }
    try:
        result = supabase.table("tax_records").insert(record).execute()
        return result.data[0]
    except Exception as e:
        logger.error(f"save_tax_record error: {e}")
        return None



# ── Team Operations ──────────────────────────────────────────────────────

async def create_team(
    owner_id: str,
    name: str,
    business_name: str = "",
    plan: str = "free",
    max_members: int = 1,
) -> Optional[dict]:
    """Create a new team and add the owner as a member."""
    import uuid as _uuid
    team_id = str(_uuid.uuid4())
    team = {
        "id":            team_id,
        "name":          name,
        "business_name": business_name,
        "owner_id":      owner_id,
        "plan":          plan,
        "max_members":   max_members,
        "created_at":    datetime.now(timezone.utc).isoformat(),
    }
    try:
        result = supabase.table("teams").insert(team).execute()
        team_data = result.data[0]

        member = {
            "id":      str(_uuid.uuid4()),
            "team_id": team_id,
            "user_id": owner_id,
            "role":    "owner",
        }
        supabase.table("team_members").insert(member).execute()

        supabase.table("users").update({"team_id": team_id}).eq("id", owner_id).execute()

        return team_data
    except Exception as e:
        logger.error(f"create_team error: {e}")
        return None


async def get_user_team(user_id: str) -> Optional[dict]:
    """Get the team a user belongs to."""
    try:
        result = (
            supabase.table("team_members")
            .select("team_id, role, teams(*)")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"get_user_team error: {e}")
        return None


async def get_team_members(team_id: str) -> list[dict]:
    """List all members of a team."""
    try:
        result = (
            supabase.table("team_members")
            .select("*, users(full_name, username, telegram_id)")
            .eq("team_id", team_id)
            .order("joined_at")
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"get_team_members error: {e}")
        return []


async def create_team_invitation(
    team_id: str,
    role: str,
    created_by: str,
    invited_email: str = "",
    invited_phone: str = "",
    expires_hours: int = 72,
) -> Optional[dict]:
    """Create an invitation to join a team."""
    import uuid as _uuid
    import secrets
    from datetime import timedelta

    invite_code = secrets.token_urlsafe(16)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=expires_hours)).isoformat()

    invitation = {
        "id":            str(_uuid.uuid4()),
        "team_id":       team_id,
        "invite_code":   invite_code,
        "role":          role,
        "invited_email": invited_email,
        "invited_phone": invited_phone,
        "created_by":    created_by,
        "expires_at":    expires_at,
    }
    try:
        result = supabase.table("team_invitations").insert(invitation).execute()
        return result.data[0]
    except Exception as e:
        logger.error(f"create_team_invitation error: {e}")
        return None


async def accept_team_invitation(invite_code: str, user_id: str) -> Optional[dict]:
    """Accept a team invitation and join the team."""
    import uuid as _uuid

    try:
        result = (
            supabase.table("team_invitations")
            .select("*")
            .eq("invite_code", invite_code)
            .eq("status", "pending")
            .single()
            .execute()
        )
        invitation = result.data
        if not invitation:
            return None

        expires_at = invitation.get("expires_at", "")
        if expires_at and datetime.fromisoformat(expires_at.replace("Z", "+00:00")) < datetime.now(timezone.utc):
            supabase.table("team_invitations").update({"status": "expired"}).eq("id", invitation["id"]).execute()
            return None

        team_id = invitation["team_id"]

        member = {
            "id":         str(_uuid.uuid4()),
            "team_id":    team_id,
            "user_id":    user_id,
            "role":       invitation["role"],
            "invited_by": invitation["created_by"],
        }
        supabase.table("team_members").insert(member).execute()

        supabase.table("users").update({"team_id": team_id}).eq("id", user_id).execute()

        supabase.table("team_invitations").update({
            "status": "accepted",
            "accepted_by": user_id,
        }).eq("id", invitation["id"]).execute()

        return invitation
    except Exception as e:
        logger.error(f"accept_team_invitation error: {e}")
        return None


async def remove_team_member(team_id: str, user_id: str) -> bool:
    """Remove a member from a team."""
    try:
        supabase.table("team_members").delete().eq("team_id", team_id).eq("user_id", user_id).execute()
        supabase.table("users").update({"team_id": None}).eq("id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"remove_team_member error: {e}")
        return False


async def get_tax_records(
    user_id: str,
    tax_type: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """Fetch tax records for a user."""
    try:
        query = (
            supabase.table("tax_records")
            .select("*")
            .eq("user_id", user_id)
            .order("period_end", desc=True)
        )
        if tax_type:
            query = query.eq("tax_type", tax_type)
        query = query.limit(limit)
        result = query.execute()
        return result.data or []
    except Exception as e:
        logger.error(f"get_tax_records error: {e}")
        return []
