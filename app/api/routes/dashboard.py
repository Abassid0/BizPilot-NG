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
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db.client import (
    get_user_by_telegram_id,
    get_user_documents,
    get_business_profile,
    save_business_profile,
    update_user_profile,
)
from app.core.constants import SubscriptionTier, TIER_LABELS, TIER_PRICES_NAIRA, DOC_TYPE_LABELS

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


# ── Auth Helper ───────────────────────────────────────────────────────────────

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

@router.get("/user/{telegram_id}")
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


@router.put("/user/{telegram_id}/profile")
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


@router.get("/user/{telegram_id}/documents")
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


@router.get("/user/{telegram_id}/stats")
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
                "docs_limit":  5,
                "features":    [
                    "5 documents per month",
                    "All 6 document types",
                    "In-chat text preview",
                    "Nigerian formatting",
                ],
                "cta": "Current Plan",
            },
            {
                "tier":        "pro",
                "label":       "Pro Operator",
                "price_naira": 4999,
                "docs_limit":  999999,
                "features":    [
                    "Unlimited documents",
                    "PDF & DOCX downloads",
                    "No watermarks",
                    "Priority generation",
                    "Document history (1 year)",
                ],
                "cta": "Upgrade to Pro",
                "popular": True,
            },
            {
                "tier":        "commander",
                "label":       "Business Commander",
                "price_naira": 12999,
                "docs_limit":  999999,
                "features":    [
                    "Everything in Pro",
                    "Custom logo on documents",
                    "3 team member seats",
                    "Dedicated support",
                    "Bulk document generation",
                ],
                "cta": "Upgrade to Commander",
            },
        ]
    }


@router.get("/health")
async def health():
    return {"status": "ok", "service": "BizPilot NG API"}
