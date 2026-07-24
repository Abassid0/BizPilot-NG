"""
app/api/routes/automation.py
-------------------------------
REST API endpoints for n8n and automation webhooks.

These endpoints are called by n8n workflows to:
  - Trigger weekly/monthly financial reports
  - Reset monthly doc counts
  - Send tax filing reminders
  - Fire custom webhook events
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Request
from loguru import logger

from app.core.config import settings
from app.api.routes.dashboard import verify_api_key
from app.db.client import (
    get_user_by_telegram_id,
    get_expense_summary,
    get_income_summary,
    supabase,
)

router = APIRouter(prefix="/api/v1/automation", tags=["automation"])


@router.post("/weekly-report/{telegram_id}", dependencies=[Depends(verify_api_key)])
async def trigger_weekly_report(telegram_id: int, request: Request):
    """
    Called by n8n weekly cron to send a financial summary to the user via Telegram.
    """
    user = await get_user_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(timezone.utc)
    expenses = await get_expense_summary(user["id"], year=now.year, month=now.month)
    income = await get_income_summary(user["id"], year=now.year, month=now.month)

    exp_total = expenses["total"]
    inc_total = income["total"]
    profit = inc_total - exp_total

    lines = [
        f"*Weekly Financial Update*\n",
        f"*Income this month:* ₦{inc_total:,.0f}",
        f"*Expenses this month:* ₦{exp_total:,.0f}",
        f"*Net {'Profit' if profit >= 0 else 'Loss'}:* ₦{abs(profit):,.0f}",
    ]

    if expenses["by_category"]:
        lines.append("\n*Top expenses:*")
        for cat, amt in list(expenses["by_category"].items())[:3]:
            lines.append(f"  {cat}: ₦{amt:,.0f}")

    lines.append("\nType /dashboard for the full breakdown.")

    try:
        bot_app = request.app.state.bot_app
        await bot_app.bot.send_message(
            chat_id=telegram_id,
            text="\n".join(lines),
            parse_mode="Markdown",
        )
        return {"success": True, "message": "Weekly report sent"}
    except Exception as e:
        logger.error(f"Failed to send weekly report to {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monthly-reset", dependencies=[Depends(verify_api_key)])
async def trigger_monthly_reset():
    """
    Called by n8n on the 1st of each month to reset document counters.
    Replaces the need for pg_cron.
    """
    try:
        supabase.rpc("reset_monthly_doc_counts", {}).execute()
        logger.info("Monthly doc count reset completed via automation API")
        return {"success": True, "message": "Monthly reset completed"}
    except Exception as e:
        logger.error(f"Monthly reset error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tax-reminder/{telegram_id}", dependencies=[Depends(verify_api_key)])
async def trigger_tax_reminder(telegram_id: int, request: Request):
    """
    Called by n8n before the 21st of each month to remind about VAT/WHT filing.
    """
    user = await get_user_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(timezone.utc)
    days_until = 21 - now.day
    if days_until < 0:
        return {"success": True, "message": "Past filing date, skipping"}

    income = await get_income_summary(user["id"], year=now.year, month=now.month)
    vat_due = income["total"] * 0.075

    text = (
        f"*Tax Filing Reminder*\n\n"
        f"VAT/WHT returns are due on the *21st* ({days_until} days away).\n\n"
        f"Estimated VAT payable this month: *₦{vat_due:,.0f}*\n\n"
        f"Type /tax for your full tax summary."
    )

    try:
        bot_app = request.app.state.bot_app
        await bot_app.bot.send_message(
            chat_id=telegram_id,
            text=text,
            parse_mode="Markdown",
        )
        return {"success": True, "message": "Tax reminder sent"}
    except Exception as e:
        logger.error(f"Tax reminder error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def automation_health():
    return {"status": "ok", "service": "BizPilot Automation API"}
