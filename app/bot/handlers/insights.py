"""
app/bot/handlers/insights.py
-------------------------------
AI-generated business health reports, trend analysis, and anomaly detection.
  /insights — Weekly/monthly health report with actionable recommendations
"""

from __future__ import annotations

from datetime import datetime, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from loguru import logger

from app.bot.keyboards.menus import back_to_main_keyboard
from app.db.client import (
    get_user_by_telegram_id,
    get_expense_summary,
    get_income_summary,
    get_user_expenses,
)
from app.services.ai.claude_client import generate_business_insights


async def insights_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show business insights menu."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Monthly Health Report", callback_data="insights:monthly")],
        [InlineKeyboardButton("Spending Trends", callback_data="insights:trends")],
        [InlineKeyboardButton("Anomaly Check", callback_data="insights:anomalies")],
        [InlineKeyboardButton("Main Menu", callback_data="menu:main")],
    ])
    await _send(update,
        "*Business Insights*\n\n"
        "Get AI-powered analysis of your business performance:",
        reply_markup=keyboard,
    )


async def insights_monthly(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    tg_id = update.effective_user.id
    user = await get_user_by_telegram_id(tg_id)
    if not user:
        await query.edit_message_text("Please /start first.")
        return

    await query.edit_message_text("Generating your business health report...")

    now = datetime.now(timezone.utc)
    cur_exp = await get_expense_summary(user["id"], year=now.year, month=now.month)
    cur_inc = await get_income_summary(user["id"], year=now.year, month=now.month)

    if now.month == 1:
        prev_y, prev_m = now.year - 1, 12
    else:
        prev_y, prev_m = now.year, now.month - 1

    prev_exp = await get_expense_summary(user["id"], year=prev_y, month=prev_m)
    prev_inc = await get_income_summary(user["id"], year=prev_y, month=prev_m)

    financial_data = {
        "current_month": {
            "period": now.strftime("%B %Y"),
            "income": cur_inc,
            "expenses": cur_exp,
            "net_profit": cur_inc["total"] - cur_exp["total"],
        },
        "previous_month": {
            "period": f"{prev_y}-{prev_m:02d}",
            "income": prev_inc,
            "expenses": prev_exp,
            "net_profit": prev_inc["total"] - prev_exp["total"],
        },
        "business_name": (user.get("business_profile") or {}).get("business_name", ""),
        "business_type": (user.get("business_profile") or {}).get("business_type", ""),
    }

    result = await generate_business_insights(financial_data, report_type="monthly")

    if not result:
        await query.edit_message_text(
            "Could not generate insights right now. Try again later.",
            reply_markup=back_to_main_keyboard(),
        )
        return

    month_name = now.strftime("%B %Y")
    lines = [f"*Business Health Report — {month_name}*\n"]

    health_score = result.get("health_score", 0)
    score_emoji = "🟢" if health_score >= 70 else "🟡" if health_score >= 40 else "🔴"
    lines.append(f"*Health Score:* {score_emoji} {health_score}/100\n")

    if result.get("summary"):
        lines.append(f"{result['summary']}\n")

    if result.get("strengths"):
        lines.append("*Strengths:*")
        for s in result["strengths"][:3]:
            lines.append(f"  ✅ {s}")
        lines.append("")

    if result.get("concerns"):
        lines.append("*Areas of Concern:*")
        for c in result["concerns"][:3]:
            lines.append(f"  ⚠️ {c}")
        lines.append("")

    if result.get("actions"):
        lines.append("*Recommended Actions:*")
        for i, a in enumerate(result["actions"][:3], 1):
            lines.append(f"  {i}. {a}")

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Spending Trends", callback_data="insights:trends")],
            [InlineKeyboardButton("Back", callback_data="insights:menu")],
            [InlineKeyboardButton("Main Menu", callback_data="menu:main")],
        ]),
    )


async def insights_trends(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    tg_id = update.effective_user.id
    user = await get_user_by_telegram_id(tg_id)
    if not user:
        await query.edit_message_text("Please /start first.")
        return

    await query.edit_message_text("Analyzing spending trends...")

    now = datetime.now(timezone.utc)
    months_data = []
    for offset in range(3):
        m = now.month - offset
        y = now.year
        if m <= 0:
            m += 12
            y -= 1
        exp = await get_expense_summary(user["id"], year=y, month=m)
        inc = await get_income_summary(user["id"], year=y, month=m)
        from calendar import month_abbr
        months_data.append({
            "month": f"{month_abbr[m]} {y}",
            "income": inc["total"],
            "expenses": exp["total"],
            "profit": inc["total"] - exp["total"],
            "top_categories": dict(list(exp["by_category"].items())[:5]),
        })

    months_data.reverse()

    lines = ["*Spending Trends (Last 3 Months)*\n"]

    for md in months_data:
        profit_label = "Profit" if md["profit"] >= 0 else "Loss"
        lines.append(
            f"*{md['month']}:* "
            f"Inc ₦{md['income']:,.0f} | Exp ₦{md['expenses']:,.0f} | "
            f"{profit_label} ₦{abs(md['profit']):,.0f}"
        )

    lines.append("")

    if len(months_data) >= 2:
        latest = months_data[-1]
        prev = months_data[-2]
        if prev["expenses"] > 0:
            exp_change = ((latest["expenses"] - prev["expenses"]) / prev["expenses"]) * 100
            direction = "📈" if exp_change > 0 else "📉"
            lines.append(f"*Expense trend:* {direction} {abs(exp_change):.1f}% vs last month")
        if prev["income"] > 0:
            inc_change = ((latest["income"] - prev["income"]) / prev["income"]) * 100
            direction = "📈" if inc_change > 0 else "📉"
            lines.append(f"*Income trend:* {direction} {abs(inc_change):.1f}% vs last month")

    all_cats: dict[str, float] = {}
    for md in months_data:
        for cat, amt in md.get("top_categories", {}).items():
            all_cats[cat] = all_cats.get(cat, 0) + amt
    if all_cats:
        sorted_cats = sorted(all_cats.items(), key=lambda x: -x[1])
        lines.append("\n*Biggest Spending Categories (3-month):*")
        for cat, amt in sorted_cats[:5]:
            lines.append(f"  {cat}: ₦{amt:,.0f}")

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Health Report", callback_data="insights:monthly")],
            [InlineKeyboardButton("Back", callback_data="insights:menu")],
            [InlineKeyboardButton("Main Menu", callback_data="menu:main")],
        ]),
    )


async def insights_anomalies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    tg_id = update.effective_user.id
    user = await get_user_by_telegram_id(tg_id)
    if not user:
        await query.edit_message_text("Please /start first.")
        return

    await query.edit_message_text("Scanning for unusual activity...")

    now = datetime.now(timezone.utc)
    recent_expenses = await get_user_expenses(user["id"], limit=100)

    cur_exp = await get_expense_summary(user["id"], year=now.year, month=now.month)
    cur_inc = await get_income_summary(user["id"], year=now.year, month=now.month)

    if now.month == 1:
        prev_y, prev_m = now.year - 1, 12
    else:
        prev_y, prev_m = now.year, now.month - 1
    prev_exp = await get_expense_summary(user["id"], year=prev_y, month=prev_m)

    anomalies = []

    for cat, cur_amt in cur_exp["by_category"].items():
        prev_amt = prev_exp["by_category"].get(cat, 0)
        if prev_amt > 0 and cur_amt > prev_amt * 2:
            pct = ((cur_amt - prev_amt) / prev_amt) * 100
            anomalies.append(
                f"*{cat}* spending jumped {pct:.0f}% "
                f"(₦{prev_amt:,.0f} → ₦{cur_amt:,.0f})"
            )

    large_threshold = cur_exp["total"] * 0.3 if cur_exp["total"] > 0 else 50_000
    for exp in recent_expenses[:20]:
        amt = float(exp.get("amount", 0))
        if amt >= large_threshold and amt > 10_000:
            desc = exp.get("description", "Unknown")[:40]
            anomalies.append(
                f"Large expense: ₦{amt:,.0f} — {desc}"
            )

    if cur_inc["total"] > 0 and cur_exp["total"] > cur_inc["total"] * 0.9:
        anomalies.append(
            "Expenses are consuming over 90% of income this month"
        )

    lines = ["*Anomaly Detection*\n"]

    if anomalies:
        lines.append(f"Found {len(anomalies)} item(s) to review:\n")
        for a in anomalies[:6]:
            lines.append(f"  ⚠️ {a}")
    else:
        lines.append("✅ No unusual activity detected this month.")
        lines.append("Your spending patterns look normal.")

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Health Report", callback_data="insights:monthly")],
            [InlineKeyboardButton("Back", callback_data="insights:menu")],
            [InlineKeyboardButton("Main Menu", callback_data="menu:main")],
        ]),
    )


async def insights_menu_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await insights_command(update, context)


async def _send(update: Update, text: str, reply_markup=None) -> None:
    kwargs = {"text": text, "parse_mode": ParseMode.MARKDOWN}
    if reply_markup:
        kwargs["reply_markup"] = reply_markup
    if update.callback_query:
        await update.callback_query.edit_message_text(**kwargs)
    else:
        await update.message.reply_text(**kwargs)
