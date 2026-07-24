"""
app/api/routes/dashboard.py
-----------------------------
REST API endpoints consumed by the web dashboard.

All routes are prefixed /api/v1/

Authentication: Telegram-ID based for MVP.
Users arrive at the dashboard via a magic link sent from the bot.
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends, Header
from pydantic import BaseModel

from app.core.config import settings
from app.db.client import (
    get_user_by_telegram_id,
    get_user_documents,
    get_business_profile,
    save_business_profile,
    update_user_profile,
    get_expense_summary,
    get_income_summary,
    get_user_expenses,
)
from app.core.constants import SubscriptionTier, TIER_LABELS, TIER_PRICES_NAIRA, DOC_TYPE_LABELS

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


# ── Auth ─────────────────────────────────────────────────────────────────────

async def verify_api_key(authorization: str = Header(..., alias="Authorization")) -> None:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if token != settings.secret_key:
        raise HTTPException(status_code=403, detail="Invalid API key")


async def _get_user_or_404(telegram_id: int) -> dict:
    user = await get_user_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ── Models ────────────────────────────────────────────────────────────────────

class ProfileUpdateRequest(BaseModel):
    business_name:    Optional[str] = None
    business_type:    Optional[str] = None
    industry:         Optional[str] = None
    cac_number:       Optional[str] = None
    tin_number:       Optional[str] = None
    bank_name:        Optional[str] = None
    account_number:   Optional[str] = None
    account_name:     Optional[str] = None
    address:          Optional[str] = None
    email:            Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/user/{telegram_id}", dependencies=[Depends(verify_api_key)])
async def get_user(telegram_id: int):
    """
    Return the full user profile including subscription status.
    Used by the dashboard to populate the overview page.
    """
    user    = await _get_user_or_404(telegram_id)
    profile = await get_business_profile(telegram_id)

    tier = user.get("subscription", "free")

    return {
        "id":           user["id"],
        "telegram_id":  user["telegram_id"],
        "full_name":    user.get("full_name", ""),
        "username":     user.get("username", ""),
        "subscription": {
            "tier":         tier,
            "label":        TIER_LABELS.get(tier, "Free"),
            "price_naira":  TIER_PRICES_NAIRA.get(tier, 0),
            "expires_at":   user.get("sub_expires_at"),
            "docs_used":    user.get("docs_used", 0),
            "docs_limit":   user.get("docs_limit", 5),
        },
        "profile": profile,
        "created_at": user.get("created_at"),
    }


@router.put("/user/{telegram_id}/profile", dependencies=[Depends(verify_api_key)])
async def update_profile(telegram_id: int, body: ProfileUpdateRequest):
    """
    Update a user's business profile from the web dashboard.
    """
    user = await _get_user_or_404(telegram_id)

    profile_updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not profile_updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Merge with existing profile
    existing = await get_business_profile(telegram_id) or {}
    merged   = {**existing, **profile_updates}

    await save_business_profile(telegram_id, merged)

    # Update email at user level too if provided
    if body.email:
        await update_user_profile(telegram_id, {"email": body.email})

    return {"success": True, "profile": merged}


@router.get("/user/{telegram_id}/documents", dependencies=[Depends(verify_api_key)])
async def get_documents(
    telegram_id: int,
    limit: int = Query(default=20, le=50),
    offset: int = Query(default=0),
):
    """
    Return paginated document history for the dashboard.
    """
    user  = await _get_user_or_404(telegram_id)
    docs  = await get_user_documents(user["id"], limit=limit)

    formatted = []
    for doc in docs:
        formatted.append({
            "id":          doc["id"],
            "type":        doc["doc_type"],
            "type_label":  DOC_TYPE_LABELS.get(doc["doc_type"], doc["doc_type"]),
            "format":      doc.get("output_format", "text"),
            "file_url":    doc.get("file_url"),
            "created_at":  doc.get("created_at"),
        })

    return {
        "documents": formatted,
        "total":     len(formatted),
        "limit":     limit,
        "offset":    offset,
    }


@router.get("/user/{telegram_id}/stats", dependencies=[Depends(verify_api_key)])
async def get_stats(telegram_id: int):
    """
    Dashboard summary stats — document counts by type, usage this month.
    """
    user = await _get_user_or_404(telegram_id)
    docs = await get_user_documents(user["id"], limit=200)

    by_type = {}
    for doc in docs:
        t = doc["doc_type"]
        by_type[t] = by_type.get(t, 0) + 1

    return {
        "total_documents":  len(docs),
        "documents_by_type": by_type,
        "docs_used_this_month": user.get("docs_used", 0),
        "docs_limit":           user.get("docs_limit", 5),
        "subscription_tier":    user.get("subscription", "free"),
    }


@router.get("/plans")
async def get_plans():
    """Return all subscription plans — used by the upgrade page."""
    return {
        "plans": [
            {
                "tier":        "free",
                "label":       "Starter",
                "price_naira": 0,
                "docs_limit":  50,
                "features":    [
                    "50 transactions per month",
                    "All document types",
                    "Basic expense tracking",
                    "In-chat text preview",
                ],
                "cta": "Current Plan",
            },
            {
                "tier":        "pro",
                "label":       "Pro",
                "price_naira": 5000,
                "docs_limit":  999999,
                "features":    [
                    "Unlimited transactions",
                    "PDF & DOCX downloads",
                    "Tax compliance & insights",
                    "AI business reports",
                    "Receipt OCR scanning",
                ],
                "cta": "Upgrade to Pro",
                "popular": True,
            },
            {
                "tier":        "business",
                "label":       "Business",
                "price_naira": 15000,
                "docs_limit":  999999,
                "features":    [
                    "Everything in Pro",
                    "Multi-user team seats",
                    "Accountant access",
                    "API access",
                    "Priority support",
                ],
                "cta": "Upgrade to Business",
            },
            {
                "tier":        "enterprise",
                "label":       "Enterprise",
                "price_naira": 0,
                "docs_limit":  999999,
                "features":    [
                    "Everything in Business",
                    "White-label for accounting firms",
                    "Custom integrations",
                    "Dedicated account manager",
                ],
                "cta": "Contact Sales",
            },
        ]
    }


@router.get("/user/{telegram_id}/finances", dependencies=[Depends(verify_api_key)])
async def get_finances(
    telegram_id: int,
    year: Optional[int] = Query(default=None),
    month: Optional[int] = Query(default=None),
):
    """Financial summary — expenses and income for a given period."""
    from datetime import datetime, timezone
    user = await _get_user_or_404(telegram_id)

    if not year or not month:
        now = datetime.now(timezone.utc)
        year, month = now.year, now.month

    expenses = await get_expense_summary(user["id"], year=year, month=month)
    income = await get_income_summary(user["id"], year=year, month=month)

    return {
        "period": f"{year}-{month:02d}",
        "income": income,
        "expenses": expenses,
        "net_profit": income["total"] - expenses["total"],
    }


@router.get("/user/{telegram_id}/expenses", dependencies=[Depends(verify_api_key)])
async def list_expenses(
    telegram_id: int,
    limit: int = Query(default=20, le=100),
    year: Optional[int] = Query(default=None),
    month: Optional[int] = Query(default=None),
):
    """List expenses for a user, optionally filtered by period."""
    user = await _get_user_or_404(telegram_id)
    expenses = await get_user_expenses(user["id"], limit=limit, year=year, month=month)
    return {"expenses": expenses, "total": len(expenses)}


@router.get("/health")
async def health():
    return {"status": "ok", "service": "BizPilot NG API"}
