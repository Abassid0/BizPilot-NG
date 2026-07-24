"""
app/bot/handlers/tax.py
-------------------------
Tax compliance handler:
  /tax — Calculate tax obligations, show filing deadlines, generate summary
"""

from __future__ import annotations

from datetime import datetime, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.constants import ParseMode
from loguru import logger

from app.bot.keyboards.menus import back_to_main_keyboard
from app.db.client import (
    get_user_by_telegram_id,
    get_expense_summary,
    get_income_summary,
    save_tax_record,
)
from app.services.ai.claude_client import calculate_tax_summary
from app.core.constants import NIGERIAN_VAT_RATE, NIGERIAN_WHT_SERVICE_RATE


async def tax_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show tax compliance menu."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("This Month", callback_data="tax:current")],
        [InlineKeyboardButton("This Quarter", callback_data="tax:quarter")],
        [InlineKeyboardButton("Filing Deadlines", callback_data="tax:deadlines")],
        [InlineKeyboardButton("Main Menu", callback_data="menu:main")],
    ])
    await _send(update,
        "*Tax Compliance*\n\n"
        "Select a period to calculate your tax obligations:",
        reply_markup=keyboard,
    )


async def tax_current_month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    tg_id = update.effective_user.id
    user = await get_user_by_telegram_id(tg_id)
    if not user:
        await query.edit_message_text("Please /start first.")
        return

    await query.edit_message_text("Calculating your tax obligations...")

    now = datetime.now(timezone.utc)
    expenses = await get_expense_summary(user["id"], year=now.year, month=now.month)
    income = await get_income_summary(user["id"], year=now.year, month=now.month)

    month_name = now.strftime("%B %Y")
    inc_total = income["total"]
    exp_total = expenses["total"]
    taxable_income = inc_total - exp_total

    vat_collected = inc_total * NIGERIAN_VAT_RATE
    wht_deducted = inc_total * NIGERIAN_WHT_SERVICE_RATE

    # CIT bracket
    annual_est = inc_total * 12
    if annual_est < 25_000_000:
        cit_rate = 0.0
        cit_bracket = "Small (< ₦25M)"
    elif annual_est < 100_000_000:
        cit_rate = 0.20
        cit_bracket = "Medium (₦25M-₦100M)"
    else:
        cit_rate = 0.30
        cit_bracket = "Large (> ₦100M)"

    est_monthly_cit = (taxable_income * cit_rate) if taxable_income > 0 else 0

    financial_data = {
        "period": month_name,
        "revenue": inc_total,
        "expenses": exp_total,
        "taxable_income": taxable_income,
        "expense_breakdown": expenses["by_category"],
        "income_breakdown": income["by_category"],
    }

    ai_summary = await calculate_tax_summary(financial_data)

    recommendations = []
    if ai_summary and ai_summary.get("recommendations"):
        recommendations = ai_summary["recommendations"][:3]

    lines = [
        f"*Tax Summary — {month_name}*\n",
        f"*Revenue:* ₦{inc_total:,.0f}",
        f"*Deductible Expenses:* ₦{exp_total:,.0f}",
        f"*Taxable Income:* ₦{taxable_income:,.0f}\n",
        "*Tax Obligations:*",
        f"  VAT (7.5%): ₦{vat_collected:,.0f}",
        f"  WHT on services (5%): ₦{wht_deducted:,.0f}",
        f"  CIT estimate ({cit_bracket}): ₦{est_monthly_cit:,.0f}\n",
    ]

    if recommendations:
        lines.append("*Recommendations:*")
        for rec in recommendations:
            lines.append(f"  - {rec}")
        lines.append("")

    next_21 = _next_filing_date(now)
    lines.append(f"*Next VAT/WHT filing:* {next_21}")

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Save Tax Record", callback_data=f"tax:save:{now.year}:{now.month}")],
            [InlineKeyboardButton("Back", callback_data="tax:menu")],
            [InlineKeyboardButton("Main Menu", callback_data="menu:main")],
        ]),
    )


async def tax_quarter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    tg_id = update.effective_user.id
    user = await get_user_by_telegram_id(tg_id)
    if not user:
        return

    await query.edit_message_text("Calculating quarterly tax obligations...")

    now = datetime.now(timezone.utc)
    q_start = ((now.month - 1) // 3) * 3 + 1
    q_num = (now.month - 1) // 3 + 1

    total_inc = 0.0
    total_exp = 0.0
    for m in range(q_start, min(q_start + 3, 13)):
        inc = await get_income_summary(user["id"], year=now.year, month=m)
        exp = await get_expense_summary(user["id"], year=now.year, month=m)
        total_inc += inc["total"]
        total_exp += exp["total"]

    taxable = total_inc - total_exp
    vat = total_inc * NIGERIAN_VAT_RATE
    wht = total_inc * NIGERIAN_WHT_SERVICE_RATE

    annual_est = total_inc * 4
    if annual_est < 25_000_000:
        cit_rate, bracket = 0.0, "Small"
    elif annual_est < 100_000_000:
        cit_rate, bracket = 0.20, "Medium"
    else:
        cit_rate, bracket = 0.30, "Large"

    cit = taxable * cit_rate if taxable > 0 else 0

    lines = [
        f"*Quarterly Tax Summary — Q{q_num} {now.year}*\n",
        f"*Revenue:* ₦{total_inc:,.0f}",
        f"*Expenses:* ₦{total_exp:,.0f}",
        f"*Taxable Income:* ₦{taxable:,.0f}\n",
        f"*VAT payable:* ₦{vat:,.0f}",
        f"*WHT payable:* ₦{wht:,.0f}",
        f"*CIT estimate ({bracket}):* ₦{cit:,.0f}",
        f"\n*Total tax liability:* ₦{vat + wht + cit:,.0f}",
    ]

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Back", callback_data="tax:menu")],
            [InlineKeyboardButton("Main Menu", callback_data="menu:main")],
        ]),
    )


async def tax_deadlines(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    now = datetime.now(timezone.utc)
    next_21 = _next_filing_date(now)

    year_end = f"31 December {now.year}"
    cit_deadline = f"30 June {now.year + 1}"

    lines = [
        "*FIRS Filing Deadlines*\n",
        f"*VAT Return:* {next_21} (monthly, by the 21st)",
        f"*WHT Remittance:* {next_21} (monthly, by the 21st)",
        f"*CIT Filing:* {cit_deadline} (within 6 months of year-end)",
        f"*Annual Returns (CAC):* Within 42 days of AGM",
        f"*Financial Year-End:* {year_end}\n",
        "*Penalties for Late Filing:*",
        "  VAT: ₦5,000 first month + ₦5,000 each subsequent month",
        "  CIT: Interest at prevailing CBN rate + 10%",
        "  WHT: 10% penalty on unremitted tax",
    ]

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Back", callback_data="tax:menu")],
            [InlineKeyboardButton("Main Menu", callback_data="menu:main")],
        ]),
    )


async def tax_save_record(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")
    if len(parts) < 4:
        return

    year, month = int(parts[2]), int(parts[3])

    tg_id = update.effective_user.id
    user = await get_user_by_telegram_id(tg_id)
    if not user:
        return

    income = await get_income_summary(user["id"], year=year, month=month)
    expenses = await get_expense_summary(user["id"], year=year, month=month)

    inc_total = income["total"]
    taxable = inc_total - expenses["total"]
    vat = inc_total * NIGERIAN_VAT_RATE

    from calendar import monthrange
    last_day = monthrange(year, month)[1]

    await save_tax_record(
        user_id=user["id"],
        tax_type="vat",
        period_start=f"{year}-{month:02d}-01",
        period_end=f"{year}-{month:02d}-{last_day}",
        gross_amount=inc_total,
        tax_amount=vat,
        due_date=_next_filing_date_str(year, month),
        details={
            "revenue": inc_total,
            "expenses": expenses["total"],
            "taxable_income": taxable,
        },
    )

    await query.edit_message_text(
        f"Tax record saved for {year}-{month:02d}.\n\n"
        f"VAT payable: ₦{vat:,.0f}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Back", callback_data="tax:menu")],
            [InlineKeyboardButton("Main Menu", callback_data="menu:main")],
        ]),
    )


async def tax_menu_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await tax_command(update, context)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _next_filing_date(now: datetime) -> str:
    if now.day <= 21:
        return now.strftime(f"21 %B %Y")
    if now.month == 12:
        return f"21 January {now.year + 1}"
    from calendar import month_name
    return f"21 {month_name[now.month + 1]} {now.year}"


def _next_filing_date_str(year: int, month: int) -> str:
    if month == 12:
        return f"{year + 1}-01-21"
    return f"{year}-{month + 1:02d}-21"


async def _send(update: Update, text: str, reply_markup=None) -> None:
    kwargs = {"text": text, "parse_mode": ParseMode.MARKDOWN}
    if reply_markup:
        kwargs["reply_markup"] = reply_markup
    if update.callback_query:
        await update.callback_query.edit_message_text(**kwargs)
    else:
        await update.message.reply_text(**kwargs)
