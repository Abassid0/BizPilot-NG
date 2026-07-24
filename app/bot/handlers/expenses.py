"""
app/bot/handlers/expenses.py
------------------------------
Expense tracking handlers:
  /expense   — Manual expense entry (ConversationHandler)
  /scan      — Prompt to send a receipt photo
  photo      — Auto-OCR receipt via Claude Vision
  quick text — AI-parsed natural language expense ("spent 5k on fuel")
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

from app.core.constants import (
    EXP_AMOUNT, EXP_DESCRIPTION, EXP_CATEGORY,
    EXP_VENDOR, EXP_CONFIRM,
    EXPENSE_CATEGORIES,
)
from app.bot.keyboards.menus import back_to_main_keyboard
from app.db.client import (
    get_user_by_telegram_id,
    save_expense,
)
from app.services.ai.claude_client import analyze_receipt_image, parse_quick_expense


# ── Keyboards ────────────────────────────────────────────────────────────────

def _category_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for i, cat in enumerate(EXPENSE_CATEGORIES):
        short = cat.split(" & ")[0].split(" ")[0][:12]
        row.append(InlineKeyboardButton(short, callback_data=f"expcat:{cat}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def _confirm_expense_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Save", callback_data="expcfm:save"),
            InlineKeyboardButton("Cancel", callback_data="expcfm:cancel"),
        ],
    ])


# ── /expense — Manual Entry Flow ─────────────────────────────────────────────

async def expense_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["expense"] = {}
    await _send(update,
        "*Log an Expense*\n\n"
        "How much did you spend? (in Naira)\n\n"
        "_Example: 5000 or 15,000_",
    )
    return EXP_AMOUNT


async def expense_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = update.message.text.strip().replace(",", "").replace("₦", "")
    multiplier = 1
    if raw.lower().endswith("k"):
        raw = raw[:-1]
        multiplier = 1000

    try:
        amount = float(raw) * multiplier
    except ValueError:
        await update.message.reply_text(
            "Please enter a valid amount. Example: 5000 or 15k",
        )
        return EXP_AMOUNT

    context.user_data["expense"]["amount"] = amount
    await update.message.reply_text(
        f"Amount: *₦{amount:,.0f}*\n\nWhat was this expense for?",
        parse_mode=ParseMode.MARKDOWN,
    )
    return EXP_DESCRIPTION


async def expense_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["expense"]["description"] = update.message.text.strip()
    await update.message.reply_text(
        "Select a category:",
        reply_markup=_category_keyboard(),
    )
    return EXP_CATEGORY


async def expense_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    cat = query.data.replace("expcat:", "")
    context.user_data["expense"]["category"] = cat

    await query.edit_message_text(
        f"Category: *{cat}*\n\n"
        "Who did you pay? (vendor/shop name)\n\n"
        "_Type 'skip' to leave blank_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return EXP_VENDOR


async def expense_vendor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    val = update.message.text.strip()
    if val.lower() != "skip":
        context.user_data["expense"]["vendor"] = val

    exp = context.user_data["expense"]
    summary = (
        "*Expense Summary*\n\n"
        f"Amount: *₦{exp['amount']:,.0f}*\n"
        f"Description: {exp.get('description', '')}\n"
        f"Category: {exp.get('category', 'Miscellaneous')}\n"
        f"Vendor: {exp.get('vendor', 'N/A')}\n\n"
        "Save this expense?"
    )
    await update.message.reply_text(
        summary,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_confirm_expense_keyboard(),
    )
    return EXP_CONFIRM


async def expense_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data.replace("expcfm:", "")

    if action == "cancel":
        context.user_data.pop("expense", None)
        await query.edit_message_text(
            "Expense cancelled.",
            reply_markup=back_to_main_keyboard(),
        )
        return ConversationHandler.END

    exp = context.user_data.get("expense", {})
    tg_id = update.effective_user.id
    user = await get_user_by_telegram_id(tg_id)
    if not user:
        await query.edit_message_text("Please /start first.")
        return ConversationHandler.END

    result = await save_expense(
        user_id=user["id"],
        amount=exp["amount"],
        description=exp.get("description", ""),
        category=exp.get("category", "Miscellaneous"),
        vendor=exp.get("vendor", ""),
        source="manual",
    )

    if result:
        await query.edit_message_text(
            f"*Expense saved!*\n\n"
            f"₦{exp['amount']:,.0f} — {exp.get('description', '')}\n\n"
            f"Type /expense to log another or /dashboard for your summary.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_to_main_keyboard(),
        )
    else:
        await query.edit_message_text(
            "Failed to save expense. Please try again.",
            reply_markup=back_to_main_keyboard(),
        )

    context.user_data.pop("expense", None)
    return ConversationHandler.END


async def _cancel_expense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("expense", None)
    await update.message.reply_text(
        "Expense cancelled.",
        reply_markup=back_to_main_keyboard(),
    )
    return ConversationHandler.END


def build_expense_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("expense", expense_start),
            CallbackQueryHandler(expense_start, pattern="^action:expense$"),
        ],
        states={
            EXP_AMOUNT:      [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_amount)],
            EXP_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_description)],
            EXP_CATEGORY:    [CallbackQueryHandler(expense_category, pattern="^expcat:")],
            EXP_VENDOR:      [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_vendor)],
            EXP_CONFIRM:     [CallbackQueryHandler(expense_confirm, pattern="^expcfm:")],
        },
        fallbacks=[CommandHandler("cancel", _cancel_expense)],
        allow_reentry=True,
    )


# ── /scan — Receipt Scanning Entry Point ─────────────────────────────────────

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "*Receipt Scanner*\n\n"
        "Send me a photo of your receipt, invoice, or bill "
        "and I'll extract the expense details automatically.\n\n"
        "Supports: POS receipts, paper receipts, utility bills, bank alerts, fuel receipts.",
        parse_mode=ParseMode.MARKDOWN,
    )


# ── Photo Handler — Auto-OCR ────────────────────────────────────────────────

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process incoming photos as receipt scans."""
    msg = await update.message.reply_text("Scanning your receipt...")

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    import io
    buf = io.BytesIO()
    await file.download_to_memory(buf)
    image_bytes = buf.getvalue()

    result = await analyze_receipt_image(image_bytes, media_type="image/jpeg")

    if not result.get("success"):
        await msg.edit_text(
            "Could not read this receipt. "
            "Please try a clearer photo or log the expense manually with /expense.",
            reply_markup=back_to_main_keyboard(),
        )
        return

    tg_id = update.effective_user.id
    user = await get_user_by_telegram_id(tg_id)
    if not user:
        await msg.edit_text("Please /start first.")
        return

    amount = result.get("amount", 0)
    description = result.get("description", "")
    vendor = result.get("vendor", "")
    category = result.get("category", "Miscellaneous")
    date_str = result.get("date", "")
    confidence = result.get("confidence", 0)

    saved = await save_expense(
        user_id=user["id"],
        amount=amount,
        description=description,
        category=category,
        vendor=vendor,
        expense_date=date_str if date_str else None,
        source="ocr",
        ocr_raw=result,
    )

    items_text = ""
    if result.get("items"):
        items_lines = []
        for item in result["items"]:
            name = item.get("name", "")
            price = item.get("price", 0)
            qty = item.get("quantity", 1)
            if name:
                items_lines.append(f"  {name} x{qty} — ₦{price:,.0f}")
        if items_lines:
            items_text = "\n" + "\n".join(items_lines) + "\n"

    conf_label = "High" if confidence >= 0.8 else "Medium" if confidence >= 0.5 else "Low"

    await msg.edit_text(
        f"*Receipt Scanned!*\n\n"
        f"Amount: *₦{amount:,.0f}*\n"
        f"Vendor: {vendor or 'Unknown'}\n"
        f"Category: {category}\n"
        f"Date: {date_str or 'Today'}\n"
        f"{items_text}\n"
        f"Confidence: {conf_label}\n\n"
        f"{'Expense saved!' if saved else 'Failed to save — try /expense manually.'}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_to_main_keyboard(),
    )


# ── Quick Expense (text message that looks like an expense) ──────────────────

async def try_quick_expense(text: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Try to parse a text message as a quick expense entry.
    Returns True if it was handled as an expense, False otherwise.
    Called from the fallback handler.
    """
    expense_keywords = [
        "spent", "paid", "bought", "cost", "charged",
        "uber", "bolt", "fuel", "dstv", "rent", "salary",
    ]
    lower = text.lower()
    has_number = any(c.isdigit() for c in text)

    if not has_number or not any(kw in lower for kw in expense_keywords):
        return False

    result = await parse_quick_expense(text)
    if not result or result.get("confidence", 0) < 0.6:
        return False

    tg_id = update.effective_user.id
    user = await get_user_by_telegram_id(tg_id)
    if not user:
        return False

    amount = result.get("amount", 0)
    if amount <= 0:
        return False

    saved = await save_expense(
        user_id=user["id"],
        amount=amount,
        description=result.get("description", text),
        category=result.get("category", "Miscellaneous"),
        vendor=result.get("vendor", ""),
        source="voice",
    )

    if saved:
        await update.message.reply_text(
            f"*Expense logged!*\n\n"
            f"₦{amount:,.0f} — {result.get('description', text)}\n"
            f"Category: {result.get('category', 'Miscellaneous')}\n\n"
            f"_Type /dashboard to see your totals._",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    return False


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _send(update: Update, text: str, reply_markup=None) -> None:
    kwargs = {"text": text, "parse_mode": ParseMode.MARKDOWN}
    if reply_markup:
        kwargs["reply_markup"] = reply_markup
    if update.callback_query:
        await update.callback_query.edit_message_text(**kwargs)
    else:
        await update.message.reply_text(**kwargs)
