"""
app/bot/handlers/invoice.py
-----------------------------
Full ConversationHandler for invoice generation.

Flow:
  1. /invoice → ask client name
  2. Client email (optional — skip supported)
  3. Invoice items (guided: description | qty | price per line)
  4. Payment terms (keyboard)
  5. Bank details check (uses saved profile or asks)
  6. Confirm → generate → deliver
"""

from __future__ import annotations

from telegram import Update
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
    INV_CLIENT_NAME, INV_CLIENT_EMAIL, INV_ITEMS,
    INV_PAYMENT_TERMS, INV_BANK_DETAILS, INV_CONFIRM,
    DocType, OutputFormat, SubscriptionTier,
)
from app.bot.keyboards.menus import (
    payment_terms_keyboard,
    output_format_keyboard,
    confirm_keyboard,
    back_to_main_keyboard,
)
from app.db.client import (
    get_user_by_telegram_id,
    get_business_profile,
    check_usage_limit,
    increment_doc_count,
    save_document,
)
from app.services.ai.claude_client import generate_document
from app.services.documents.generator import DocumentGenerator
from app.services.documents.storage import upload_document


# ── Entry Point ───────────────────────────────────────────────────────────────

async def invoice_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tg_id = update.effective_user.id

    # Check usage limit before starting
    can_gen, used, limit = await check_usage_limit(tg_id)
    if not can_gen:
        await _send_or_edit(update,
            f"⚠️ You've used all *{limit} free documents* this month.\n\n"
            f"Upgrade to *Pro* for unlimited invoices and PDF downloads.",
            reply_markup=back_to_main_keyboard(),
        )
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["doc_type"] = DocType.INVOICE

    await _send_or_edit(update,
        "📄 *Invoice Generator*\n\n"
        f"You have *{limit - used} documents* remaining this month.\n\n"
        "What is the *client's name or company name*?",
        reply_markup=None,
    )
    return INV_CLIENT_NAME


async def invoice_client_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["client_name"] = update.message.text.strip()
    await update.message.reply_text(
        "What is the client's *email address*?\n\n_(Type 'skip' to leave blank)_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return INV_CLIENT_EMAIL


async def invoice_client_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    val = update.message.text.strip()
    context.user_data["client_email"] = "" if val.lower() == "skip" else val

    await update.message.reply_text(
        "📝 *Add Invoice Items*\n\n"
        "Enter each item on a new line in this format:\n"
        "`Description | Quantity | Unit Price`\n\n"
        "*Example:*\n"
        "`Web Design Service | 1 | 250000`\n"
        "`Logo Design | 2 | 75000`\n\n"
        "_(Prices in Naira, no ₦ symbol needed)_\n\n"
        "When done, tap *✅ Done* or type all items and send.",
        parse_mode=ParseMode.MARKDOWN,
    )
    return INV_ITEMS


async def invoice_items(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = update.message.text.strip()
    items = _parse_items(raw)

    if not items:
        await update.message.reply_text(
            "⚠️ I couldn't parse those items.\n\n"
            "Please use the format: `Description | Quantity | Unit Price`\n"
            "Example: `Catering Service | 1 | 350000`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return INV_ITEMS

    context.user_data["items"] = items

    # Show parsed items for confirmation
    preview = "\n".join(
        f"• {it['description']} × {it['quantity']} @ ₦{it['unit_price']:,}"
        for it in items
    )
    await update.message.reply_text(
        f"✅ *Items captured:*\n{preview}\n\nSelect *payment terms*:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=payment_terms_keyboard(),
    )
    return INV_PAYMENT_TERMS


async def invoice_payment_terms(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["payment_terms"] = query.data.replace("terms:", "")

    # Check if bank details are in profile
    profile = await get_business_profile(update.effective_user.id)
    if profile.get("bank_name") and profile.get("account_number"):
        context.user_data["bank_from_profile"] = True
        await _show_invoice_confirm(query, context, profile)
        return INV_CONFIRM

    await query.edit_message_text(
        "🏦 *Bank Details*\n\n"
        "Enter your bank details in this format:\n"
        "`Account Name | Account Number | Bank Name`\n\n"
        "_Example:_\n"
        "`Adeleke Enterprises | 0123456789 | GTBank`",
        parse_mode=ParseMode.MARKDOWN,
    )
    return INV_BANK_DETAILS


async def invoice_bank_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    parts = [p.strip() for p in update.message.text.split("|")]
    if len(parts) < 3:
        await update.message.reply_text(
            "⚠️ Please use the format:\n`Account Name | Account Number | Bank Name`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return INV_BANK_DETAILS

    context.user_data["bank_account_name"]   = parts[0]
    context.user_data["bank_account_number"] = parts[1]
    context.user_data["bank_name"]           = parts[2]

    profile = await get_business_profile(update.effective_user.id)
    await update.message.reply_text(
        _build_invoice_summary(context.user_data, profile),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=confirm_keyboard("invoice"),
    )
    return INV_CONFIRM


async def invoice_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data.replace("confirm:", "")

    if action == "cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Invoice cancelled.", reply_markup=back_to_main_keyboard())
        return ConversationHandler.END

    if action == "edit":
        await query.edit_message_text(
            "What is the *client's name*?", parse_mode=ParseMode.MARKDOWN
        )
        return INV_CLIENT_NAME

    # Generate the invoice
    await query.edit_message_text("⏳ Generating your invoice... please wait.")

    tg_id   = update.effective_user.id
    user    = await get_user_by_telegram_id(tg_id)
    profile = await get_business_profile(tg_id)

    user_data = {
        "client_name":          context.user_data.get("client_name", ""),
        "client_email":         context.user_data.get("client_email", ""),
        "items":                context.user_data.get("items", []),
        "payment_terms":        context.user_data.get("payment_terms", "Net 7"),
        "seller_bank_name":     context.user_data.get("bank_name") or profile.get("bank_name", ""),
        "seller_account_number": context.user_data.get("bank_account_number") or profile.get("account_number", ""),
        "seller_account_name":  context.user_data.get("bank_account_name") or profile.get("account_name", ""),
        "seller_name":          profile.get("business_name", user.get("full_name", "")),
        "seller_cac":           profile.get("cac_number", ""),
        "seller_tin":           profile.get("tin_number", ""),
        "seller_address":       profile.get("address", ""),
    }

    result = await generate_document(DocType.INVOICE, user_data, profile)

    if not result["success"]:
        await query.edit_message_text(
            f"⚠️ Document generation failed: {result.get('error', 'Unknown error')}\n\nPlease try again.",
            reply_markup=back_to_main_keyboard(),
        )
        return ConversationHandler.END

    tier = SubscriptionTier(user.get("subscription", "free"))
    is_free = tier == SubscriptionTier.FREE

    # Determine output format based on tier
    output_format = OutputFormat.TEXT if is_free else OutputFormat.PDF

    doc_bytes = await DocumentGenerator.generate(
        doc_type=DocType.INVOICE,
        ai_data=result["data"],
        output_format=output_format,
        subscription_tier=tier,
    )

    # Increment usage counter
    await increment_doc_count(tg_id)

    file_url = None

    if output_format == OutputFormat.TEXT or doc_bytes is None:
        # Send as formatted text in chat
        plain_text = DocumentGenerator._invoice_to_text(result["data"])
        # Telegram has 4096 char limit — split if needed
        chunks = _chunk_text(plain_text, 4000)
        for i, chunk in enumerate(chunks):
            if i == 0:
                await query.edit_message_text(f"```\n{chunk}\n```", parse_mode=ParseMode.MARKDOWN)
            else:
                await query.message.reply_text(f"```\n{chunk}\n```", parse_mode=ParseMode.MARKDOWN)

        if is_free:
            await query.message.reply_text(
                "💡 *Upgrade to Pro* to download professional PDF invoices with your branding.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=back_to_main_keyboard(),
            )
    else:
        # Upload PDF and send download link
        file_url = await upload_document(user["id"], DocType.INVOICE, doc_bytes, output_format)

        if file_url:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            await query.edit_message_text(
                "✅ *Invoice Generated!*\n\nYour professional PDF invoice is ready.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 Download Invoice PDF", url=file_url)],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="menu:main")],
                ]),
            )
        else:
            # Fallback to text if upload fails
            plain_text = DocumentGenerator._invoice_to_text(result["data"])
            await query.edit_message_text(f"```\n{plain_text[:4000]}\n```", parse_mode=ParseMode.MARKDOWN)

    # Save document to history
    await save_document(
        user_id=user["id"],
        doc_type=DocType.INVOICE,
        input_data=user_data,
        output_text=result["raw_text"],
        file_url=file_url,
        output_format=output_format,
    )

    context.user_data.clear()
    return ConversationHandler.END


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_items(raw: str) -> list[dict]:
    """Parse multi-line item input into structured list."""
    items = []
    for line in raw.strip().split("\n"):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            try:
                price = float(parts[2].replace(",", "").replace("₦", "").strip())
                qty   = float(parts[1].strip())
                items.append({
                    "description": parts[0],
                    "quantity":    qty,
                    "unit_price":  price,
                    "line_total":  qty * price,
                })
            except ValueError:
                continue
        elif len(parts) == 2:
            try:
                price = float(parts[1].replace(",", "").replace("₦", "").strip())
                items.append({
                    "description": parts[0],
                    "quantity":    1,
                    "unit_price":  price,
                    "line_total":  price,
                })
            except ValueError:
                continue
    return items


def _build_invoice_summary(data: dict, profile: dict) -> str:
    items = data.get("items", [])
    item_lines = "\n".join(
        f"  • {it['description']} × {it['quantity']} @ ₦{it['unit_price']:,}"
        for it in items
    )
    subtotal = sum(it["line_total"] for it in items)
    vat      = subtotal * 0.075
    total    = subtotal + vat

    bank_name = data.get("bank_name") or profile.get("bank_name", "Not set")
    acc_num   = data.get("bank_account_number") or profile.get("account_number", "")
    acc_name  = data.get("bank_account_name") or profile.get("account_name", "")

    return (
        f"📄 *Invoice Summary — Please Confirm*\n\n"
        f"*Client:* {data.get('client_name', '')}\n"
        f"*Email:* {data.get('client_email', 'N/A')}\n\n"
        f"*Items:*\n{item_lines}\n\n"
        f"*Subtotal:* ₦{subtotal:,.2f}\n"
        f"*VAT (7.5%):* ₦{vat:,.2f}\n"
        f"*Total Due:* ₦{total:,.2f}\n\n"
        f"*Payment Terms:* {data.get('payment_terms', '')}\n"
        f"*Bank:* {acc_name} | {acc_num} | {bank_name}\n\n"
        f"Ready to generate?"
    )


async def _show_invoice_confirm(query, context, profile):
    summary = _build_invoice_summary(context.user_data, profile)
    await query.edit_message_text(
        summary,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=confirm_keyboard("invoice"),
    )


async def _send_or_edit(update: Update, text: str, reply_markup=None) -> None:
    kwargs = {"text": text, "parse_mode": ParseMode.MARKDOWN}
    if reply_markup:
        kwargs["reply_markup"] = reply_markup
    if update.callback_query:
        await update.callback_query.edit_message_text(**kwargs)
    else:
        await update.message.reply_text(**kwargs)


def _chunk_text(text: str, size: int) -> list[str]:
    return [text[i:i+size] for i in range(0, len(text), size)]


# ── ConversationHandler Builder ───────────────────────────────────────────────

def build_invoice_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("invoice", invoice_start),
            CallbackQueryHandler(invoice_start, pattern="^doc:invoice$"),
        ],
        states={
            INV_CLIENT_NAME:   [MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_client_name)],
            INV_CLIENT_EMAIL:  [MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_client_email)],
            INV_ITEMS:         [MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_items)],
            INV_PAYMENT_TERMS: [CallbackQueryHandler(invoice_payment_terms, pattern="^terms:")],
            INV_BANK_DETAILS:  [MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_bank_details)],
            INV_CONFIRM:       [CallbackQueryHandler(invoice_confirm, pattern="^confirm:")],
        },
        fallbacks=[CommandHandler("cancel", _cancel)],
        allow_reentry=True,
    )


async def _cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("❌ Invoice cancelled.", reply_markup=back_to_main_keyboard())
    return ConversationHandler.END
