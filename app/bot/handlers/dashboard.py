"""
app/bot/handlers/dashboard.py
-------------------------------
Financial dashboard via Telegram:
  /dashboard  — Monthly P&L summary, expense breakdown, NL queries
"""

from __future__ import annotations

from datetime import datetime, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from telegram.constants import ParseMode
from loguru import logger

from app.core.constants import DASH_QUERY
from app.bot.keyboards.menus import back_to_main_keyboard
from app.db.client import (
    get_user_by_telegram_id,
    get_expense_summary,
    get_income_summary,
)
from app.services.ai.claude_client import query_financials


# ── /dashboard ────────────────────────────────────────────────────────────────

async def dashboard_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tg_id = update.effective_user.id
    user = await get_user_by_telegram_id(tg_id)
    if not user:
        await _send(update, "Please /start first.")
        return ConversationHandler.END

    now = datetime.now(timezone.utc)
    year, month = now.year, now.month

    expenses = await get_expense_summary(user["id"], year=year, month=month)
    income = await get_income_summary(user["id"], year=year, month=month)

    month_name = now.strftime("%B %Y")

    exp_total = expenses["total"]
    inc_total = income["total"]
    profit = inc_total - exp_total

    lines = [
        f"*Financial Dashboard — {month_name}*\n",
        f"*Income:* ₦{inc_total:,.0f} ({income['count']} entries)",
        f"*Expenses:* ₦{exp_total:,.0f} ({expenses['count']} entries)",
        f"*Net {'Profit' if profit >= 0 else 'Loss'}:* ₦{abs(profit):,.0f}",
        "",
    ]

    if expenses["by_category"]:
        lines.append("*Top Expenses:*")
        for cat, amt in list(expenses["by_category"].items())[:5]:
            pct = (amt / exp_total * 100) if exp_total > 0 else 0
            bar = _progress_bar(pct)
            lines.append(f"  {cat}: ₦{amt:,.0f} {bar}")
        lines.append("")

    if income["by_category"]:
        lines.append("*Income Sources:*")
        for cat, amt in list(income["by_category"].items())[:3]:
            lines.append(f"  {cat}: ₦{amt:,.0f}")
        lines.append("")

    lines.append(
        "_Ask me anything about your finances below, "
        "or tap a button for quick actions._"
    )

    context.user_data["financial_data"] = {
        "period": month_name,
        "income": income,
        "expenses": expenses,
        "net_profit": profit,
    }

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Last Month", callback_data="dash:prev_month"),
            InlineKeyboardButton("This Quarter", callback_data="dash:quarter"),
        ],
        [
            InlineKeyboardButton("Tax Summary", callback_data="dash:tax"),
            InlineKeyboardButton("Log Expense", callback_data="action:expense"),
        ],
        [InlineKeyboardButton("Main Menu", callback_data="menu:main")],
    ])

    await _send(update, "\n".join(lines), reply_markup=keyboard)
    return DASH_QUERY


async def dashboard_prev_month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    tg_id = update.effective_user.id
    user = await get_user_by_telegram_id(tg_id)
    if not user:
        return ConversationHandler.END

    now = datetime.now(timezone.utc)
    if now.month == 1:
        year, month = now.year - 1, 12
    else:
        year, month = now.year, now.month - 1

    expenses = await get_expense_summary(user["id"], year=year, month=month)
    income = await get_income_summary(user["id"], year=year, month=month)

    from calendar import month_name as mn
    month_label = f"{mn[month]} {year}"

    exp_total = expenses["total"]
    inc_total = income["total"]
    profit = inc_total - exp_total

    lines = [
        f"*Financial Summary — {month_label}*\n",
        f"*Income:* ₦{inc_total:,.0f}",
        f"*Expenses:* ₦{exp_total:,.0f}",
        f"*Net {'Profit' if profit >= 0 else 'Loss'}:* ₦{abs(profit):,.0f}",
    ]

    if expenses["by_category"]:
        lines.append("\n*Expenses by Category:*")
        for cat, amt in expenses["by_category"].items():
            lines.append(f"  {cat}: ₦{amt:,.0f}")

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Back to Dashboard", callback_data="dash:current")],
            [InlineKeyboardButton("Main Menu", callback_data="menu:main")],
        ]),
    )
    return DASH_QUERY


async def dashboard_quarter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    tg_id = update.effective_user.id
    user = await get_user_by_telegram_id(tg_id)
    if not user:
        return ConversationHandler.END

    now = datetime.now(timezone.utc)
    quarter_start_month = ((now.month - 1) // 3) * 3 + 1
    quarter_num = (now.month - 1) // 3 + 1

    total_income = 0.0
    total_expenses = 0.0
    all_exp_cats: dict[str, float] = {}

    for m in range(quarter_start_month, quarter_start_month + 3):
        y = now.year
        if m > 12:
            break
        exp = await get_expense_summary(user["id"], year=y, month=m)
        inc = await get_income_summary(user["id"], year=y, month=m)
        total_expenses += exp["total"]
        total_income += inc["total"]
        for cat, amt in exp["by_category"].items():
            all_exp_cats[cat] = all_exp_cats.get(cat, 0) + amt

    profit = total_income - total_expenses
    sorted_cats = sorted(all_exp_cats.items(), key=lambda x: -x[1])

    lines = [
        f"*Quarterly Summary — Q{quarter_num} {now.year}*\n",
        f"*Income:* ₦{total_income:,.0f}",
        f"*Expenses:* ₦{total_expenses:,.0f}",
        f"*Net {'Profit' if profit >= 0 else 'Loss'}:* ₦{abs(profit):,.0f}",
    ]

    if sorted_cats:
        lines.append("\n*Top Expense Categories:*")
        for cat, amt in sorted_cats[:5]:
            lines.append(f"  {cat}: ₦{amt:,.0f}")

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Back to Dashboard", callback_data="dash:current")],
            [InlineKeyboardButton("Main Menu", callback_data="menu:main")],
        ]),
    )
    return DASH_QUERY


async def dashboard_current(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Re-render the current month dashboard."""
    return await dashboard_start(update, context)


async def dashboard_nl_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle a natural-language financial question."""
    question = update.message.text.strip()
    financial_data = context.user_data.get("financial_data", {})

    if not financial_data:
        tg_id = update.effective_user.id
        user = await get_user_by_telegram_id(tg_id)
        if user:
            now = datetime.now(timezone.utc)
            expenses = await get_expense_summary(user["id"], year=now.year, month=now.month)
            income = await get_income_summary(user["id"], year=now.year, month=now.month)
            financial_data = {
                "period": now.strftime("%B %Y"),
                "income": income,
                "expenses": expenses,
                "net_profit": income["total"] - expenses["total"],
            }

    msg = await update.message.reply_text("Analyzing your financial data...")

    answer = await query_financials(question, financial_data)

    await msg.edit_text(
        f"*Financial Insight*\n\n{answer}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Back to Dashboard", callback_data="dash:current")],
            [InlineKeyboardButton("Main Menu", callback_data="menu:main")],
        ]),
    )
    return DASH_QUERY


async def _cancel_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Dashboard closed.", reply_markup=back_to_main_keyboard())
    return ConversationHandler.END


def build_dashboard_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("dashboard", dashboard_start),
            CallbackQueryHandler(dashboard_start, pattern="^action:dashboard$"),
        ],
        states={
            DASH_QUERY: [
                CallbackQueryHandler(dashboard_prev_month, pattern="^dash:prev_month$"),
                CallbackQueryHandler(dashboard_quarter, pattern="^dash:quarter$"),
                CallbackQueryHandler(dashboard_current, pattern="^dash:current$"),
                CallbackQueryHandler(dashboard_start, pattern="^dash:tax$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, dashboard_nl_query),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", _cancel_dashboard),
            CallbackQueryHandler(
                lambda u, c: ConversationHandler.END,
                pattern="^menu:main$",
            ),
        ],
        allow_reentry=True,
    )


# ── Helpers ──────────────────────────────────────────────────────────────────

def _progress_bar(pct: float, width: int = 8) -> str:
    filled = int(pct / 100 * width)
    return "[" + "#" * filled + "." * (width - filled) + f"] {pct:.0f}%"


async def _send(update: Update, text: str, reply_markup=None) -> None:
    kwargs = {"text": text, "parse_mode": ParseMode.MARKDOWN}
    if reply_markup:
        kwargs["reply_markup"] = reply_markup
    if update.callback_query:
        await update.callback_query.edit_message_text(**kwargs)
    else:
        await update.message.reply_text(**kwargs)
