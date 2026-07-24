"""
app/bot/handlers/documents.py
------------------------------
ConversationHandlers for all document types except Invoice
(which has its own dedicated file due to complexity):

  - Proposal
  - Contract
  - Social Post
  - Customer Reply
  - Business Plan
  - Voice message (transcription → route to doc type)
"""

from __future__ import annotations

import io
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
    # Proposal states
    PROP_CLIENT_NAME, PROP_PROJECT_DESC, PROP_DELIVERABLES,
    PROP_AMOUNT, PROP_TIMELINE, PROP_CONFIRM,
    # Contract states
    CONT_TYPE, CONT_PARTY_A, CONT_PARTY_B, CONT_SCOPE,
    CONT_VALUE, CONT_DURATION, CONT_CONFIRM,
    # Social states
    SOC_PLATFORM, SOC_PRODUCT, SOC_TONE, SOC_CTA, SOC_CONFIRM,
    # Reply states
    REPLY_CONTEXT, REPLY_ISSUE, REPLY_TONE, REPLY_CONFIRM,
    # BizPlan states
    BIZPLAN_DESC, BIZPLAN_MARKET, BIZPLAN_REVENUE,
    BIZPLAN_PURPOSE, BIZPLAN_CONFIRM,
    DocType, OutputFormat, SubscriptionTier, DOC_TYPE_LABELS,
)
from app.bot.keyboards.menus import (
    contract_type_keyboard,
    social_platform_keyboard,
    tone_keyboard,
    output_format_keyboard,
    confirm_keyboard,
    back_to_main_keyboard,
)
from app.db.client import (
    get_user_by_telegram_id,
    get_business_profile,
    check_usage_limit,
    increment_doc_count,
    check_and_send_usage_warning,
    save_document,
)
from app.services.ai.claude_client import generate_document, transcribe_voice
from app.services.documents.generator import DocumentGenerator
from app.services.documents.storage import upload_document


# ════════════════════════════════════════════════════════════════
# SHARED HELPERS
# ════════════════════════════════════════════════════════════════

async def _check_and_warn(update: Update) -> bool:
    """Returns True if user can generate. Sends warning and returns False if not."""
    tg_id = update.effective_user.id
    can_gen, used, limit = await check_usage_limit(tg_id)
    if not can_gen:
        text = (
            f"⚠️ You've used all *{limit} free documents* this month.\n\n"
            "Upgrade to *Pro* for unlimited documents."
        )
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_to_main_keyboard()
            )
        else:
            await update.message.reply_text(
                text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_to_main_keyboard()
            )
    return can_gen


async def _deliver_document(
    update: Update,
    doc_type: DocType,
    result: dict,
    user: dict,
    user_input: dict,
) -> None:
    """Common delivery logic for all document types."""
    import io as _io
    from datetime import datetime, timezone
    tier     = SubscriptionTier(user.get("subscription", "free"))
    is_free  = tier == SubscriptionTier.FREE
    msg = update.callback_query.message if update.callback_query else update.message
    label = DOC_TYPE_LABELS.get(doc_type, doc_type)

    plain = DocumentGenerator._to_plain_text(doc_type, result["data"])
    chunks = [plain[i:i+4000] for i in range(0, len(plain), 4000)]
    for i, chunk in enumerate(chunks):
        if i == 0 and update.callback_query:
            await update.callback_query.edit_message_text(
                f"```\n{chunk}\n```", parse_mode=ParseMode.MARKDOWN
            )
        else:
            await msg.reply_text(f"```\n{chunk}\n```", parse_mode=ParseMode.MARKDOWN)

    docx_bytes = await DocumentGenerator.generate(
        doc_type=doc_type,
        ai_data=result["data"],
        output_format=OutputFormat.DOCX,
        subscription_tier=tier,
    )
    if docx_bytes:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d")
        filename = f"BizPilot_{doc_type}_{ts}.docx"
        await msg.reply_document(
            document=_io.BytesIO(docx_bytes),
            filename=filename,
            caption=f"📎 {label} — tap to download",
        )

    file_url = None
    if not is_free:
        pdf_bytes = await DocumentGenerator.generate(
            doc_type=doc_type,
            ai_data=result["data"],
            output_format=OutputFormat.PDF,
            subscription_tier=tier,
        )
        if pdf_bytes:
            file_url = await upload_document(user["id"], doc_type, pdf_bytes, OutputFormat.PDF)

    await increment_doc_count(update.effective_user.id)
    await check_and_send_usage_warning(update.effective_user.id)

    if is_free:
        await msg.reply_text(
            "💡 *Upgrade to Pro* for professional PDF downloads with branding.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_to_main_keyboard(),
        )
    else:
        await msg.reply_text(
            "✅ *Document generated!*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_to_main_keyboard(),
        )

    await save_document(
        user_id=user["id"],
        doc_type=doc_type,
        input_data=user_input,
        output_text=result["raw_text"],
        file_url=file_url,
        output_format=OutputFormat.DOCX,
    )


async def _cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("❌ Cancelled.", reply_markup=back_to_main_keyboard())
    return ConversationHandler.END


# ════════════════════════════════════════════════════════════════
# BUSINESS PROPOSAL
# ════════════════════════════════════════════════════════════════

async def proposal_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _check_and_warn(update):
        return ConversationHandler.END
    context.user_data.clear()
    context.user_data["doc_type"] = DocType.PROPOSAL

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "📋 *Business Proposal Writer*\n\nWhat is the *client's name or company*?",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await update.message.reply_text(
            "📋 *Business Proposal Writer*\n\nWhat is the *client's name or company*?",
            parse_mode=ParseMode.MARKDOWN,
        )
    return PROP_CLIENT_NAME


async def proposal_client(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["client_name"] = update.message.text.strip()
    await update.message.reply_text(
        "Describe the *project or service* you are proposing:\n\n"
        "_e.g. 'Website redesign and social media management for 3 months'_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return PROP_PROJECT_DESC


async def proposal_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["project_description"] = update.message.text.strip()
    await update.message.reply_text(
        "List the *key deliverables* (one per line):\n\n"
        "_e.g._\n"
        "_5-page website design_\n"
        "_3 social media posts per week_\n"
        "_Monthly performance report_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return PROP_DELIVERABLES


async def proposal_deliverables(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = update.message.text.strip()
    context.user_data["deliverables"] = [line.strip() for line in raw.split("\n") if line.strip()]
    await update.message.reply_text(
        "What is the *total project value*? (Naira amount only, e.g. 450000)"
    )
    return PROP_AMOUNT


async def proposal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        amount = float(update.message.text.strip().replace(",", "").replace("₦", ""))
        context.user_data["total_amount"] = amount
    except ValueError:
        await update.message.reply_text("⚠️ Please enter a number only, e.g. 450000")
        return PROP_AMOUNT

    await update.message.reply_text(
        "What is the *project timeline*?\n\n_e.g. '4 weeks', '3 months', 'By 30 August 2026'_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return PROP_TIMELINE


async def proposal_timeline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["timeline"] = update.message.text.strip()

    summary = (
        f"📋 *Proposal Summary*\n\n"
        f"*Client:* {context.user_data.get('client_name')}\n"
        f"*Project:* {context.user_data.get('project_description', '')[:80]}...\n"
        f"*Value:* ₦{context.user_data.get('total_amount', 0):,.2f}\n"
        f"*Timeline:* {context.user_data.get('timeline')}\n\n"
        f"Generate proposal?"
    )
    await update.message.reply_text(
        summary, parse_mode=ParseMode.MARKDOWN, reply_markup=confirm_keyboard("proposal")
    )
    return PROP_CONFIRM


async def proposal_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data.replace("confirm:", "")

    if action == "cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Proposal cancelled.", reply_markup=back_to_main_keyboard())
        return ConversationHandler.END

    if action == "edit":
        await query.edit_message_text("What is the *client's name*?", parse_mode=ParseMode.MARKDOWN)
        return PROP_CLIENT_NAME

    await query.edit_message_text("⏳ Writing your proposal...")

    tg_id   = update.effective_user.id
    user    = await get_user_by_telegram_id(tg_id)
    profile = await get_business_profile(tg_id)

    user_input = {
        "client_name":        context.user_data.get("client_name"),
        "project_description": context.user_data.get("project_description"),
        "deliverables":       context.user_data.get("deliverables", []),
        "total_amount":       context.user_data.get("total_amount", 0),
        "timeline":           context.user_data.get("timeline"),
        "sender_name":        user.get("full_name", ""),
        "sender_business":    profile.get("business_name", ""),
        "payment_schedule":   "50% upfront, 50% on completion",
        "validity_days":      14,
    }

    result = await generate_document(DocType.PROPOSAL, user_input, profile)
    if not result["success"]:
        await query.edit_message_text(
            "⚠️ Generation failed. Please try again.", reply_markup=back_to_main_keyboard()
        )
        return ConversationHandler.END

    await _deliver_document(update, DocType.PROPOSAL, result, user, user_input)
    context.user_data.clear()
    return ConversationHandler.END


def build_proposal_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("proposal", proposal_start),
            CallbackQueryHandler(proposal_start, pattern="^doc:proposal$"),
        ],
        states={
            PROP_CLIENT_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, proposal_client)],
            PROP_PROJECT_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, proposal_description)],
            PROP_DELIVERABLES: [MessageHandler(filters.TEXT & ~filters.COMMAND, proposal_deliverables)],
            PROP_AMOUNT:       [MessageHandler(filters.TEXT & ~filters.COMMAND, proposal_amount)],
            PROP_TIMELINE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, proposal_timeline)],
            PROP_CONFIRM:      [CallbackQueryHandler(proposal_confirm, pattern="^confirm:")],
        },
        fallbacks=[CommandHandler("cancel", _cancel)],
        allow_reentry=True,
    )


# ════════════════════════════════════════════════════════════════
# CONTRACT / NDA
# ════════════════════════════════════════════════════════════════

async def contract_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _check_and_warn(update):
        return ConversationHandler.END
    context.user_data.clear()

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "📝 *Contract Generator*\n\nWhat type of contract do you need?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=contract_type_keyboard(),
        )
    else:
        await update.message.reply_text(
            "📝 *Contract Generator*\n\nWhat type of contract do you need?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=contract_type_keyboard(),
        )
    return CONT_TYPE


async def contract_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["contract_type"] = query.data.replace("conttype:", "")
    await query.edit_message_text(
        "Enter *Party A* details (your business):\n`Name | Address`\n\n_e.g. Adewale Logistics Ltd | 15 Marina Street, Lagos Island_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return CONT_PARTY_A


async def contract_party_a(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    parts = [p.strip() for p in update.message.text.split("|")]
    context.user_data["party_a_name"]    = parts[0]
    context.user_data["party_a_address"] = parts[1] if len(parts) > 1 else ""
    await update.message.reply_text(
        "Enter *Party B* details (client/other party):\n`Name | Address`",
        parse_mode=ParseMode.MARKDOWN,
    )
    return CONT_PARTY_B


async def contract_party_b(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    parts = [p.strip() for p in update.message.text.split("|")]
    context.user_data["party_b_name"]    = parts[0]
    context.user_data["party_b_address"] = parts[1] if len(parts) > 1 else ""
    await update.message.reply_text(
        "Briefly describe the *scope of work or purpose* of this contract:"
    )
    return CONT_SCOPE


async def contract_scope(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["scope_of_work"] = update.message.text.strip()
    await update.message.reply_text(
        "What is the *contract value*? (Naira amount, or type 'nil' for NDAs)"
    )
    return CONT_VALUE


async def contract_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    val = update.message.text.strip()
    context.user_data["contract_value"] = 0 if val.lower() == "nil" else val.replace(",", "").replace("₦", "")
    await update.message.reply_text(
        "What is the *contract duration*?\n_e.g. 6 months, 1 year, Ongoing_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return CONT_DURATION


async def contract_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["duration"] = update.message.text.strip()
    summary = (
        f"📝 *Contract Summary*\n\n"
        f"*Type:* {context.user_data.get('contract_type', '').replace('_', ' ').title()}\n"
        f"*Party A:* {context.user_data.get('party_a_name')}\n"
        f"*Party B:* {context.user_data.get('party_b_name')}\n"
        f"*Duration:* {context.user_data.get('duration')}\n\n"
        f"Generate contract?"
    )
    await update.message.reply_text(
        summary, parse_mode=ParseMode.MARKDOWN, reply_markup=confirm_keyboard("contract")
    )
    return CONT_CONFIRM


async def contract_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "confirm:cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Cancelled.", reply_markup=back_to_main_keyboard())
        return ConversationHandler.END

    await query.edit_message_text("⏳ Drafting your contract...")

    tg_id   = update.effective_user.id
    user    = await get_user_by_telegram_id(tg_id)
    profile = await get_business_profile(tg_id)

    user_input = {k: v for k, v in context.user_data.items()}
    result = await generate_document(DocType.CONTRACT, user_input, profile)

    if not result["success"]:
        await query.edit_message_text("⚠️ Generation failed.", reply_markup=back_to_main_keyboard())
        return ConversationHandler.END

    await _deliver_document(update, DocType.CONTRACT, result, user, user_input)
    context.user_data.clear()
    return ConversationHandler.END


def build_contract_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("contract", contract_start),
            CallbackQueryHandler(contract_start, pattern="^doc:contract$"),
        ],
        states={
            CONT_TYPE:    [CallbackQueryHandler(contract_type, pattern="^conttype:")],
            CONT_PARTY_A: [MessageHandler(filters.TEXT & ~filters.COMMAND, contract_party_a)],
            CONT_PARTY_B: [MessageHandler(filters.TEXT & ~filters.COMMAND, contract_party_b)],
            CONT_SCOPE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, contract_scope)],
            CONT_VALUE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, contract_value)],
            CONT_DURATION:[MessageHandler(filters.TEXT & ~filters.COMMAND, contract_duration)],
            CONT_CONFIRM: [CallbackQueryHandler(contract_confirm, pattern="^confirm:")],
        },
        fallbacks=[CommandHandler("cancel", _cancel)],
        allow_reentry=True,
    )


# ════════════════════════════════════════════════════════════════
# SOCIAL MEDIA POST
# ════════════════════════════════════════════════════════════════

async def social_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _check_and_warn(update):
        return ConversationHandler.END
    context.user_data.clear()

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "📱 *Social Media Content*\n\nWhich platform?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=social_platform_keyboard(),
        )
    else:
        await update.message.reply_text(
            "📱 *Social Media Content*\n\nWhich platform?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=social_platform_keyboard(),
        )
    return SOC_PLATFORM


async def social_platform(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["platform"] = query.data.replace("platform:", "")
    await query.edit_message_text(
        "What *product or service* are you promoting?\n\n_e.g. 'Our new pepper soup catering package'_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return SOC_PRODUCT


async def social_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["product_or_service"] = update.message.text.strip()
    await update.message.reply_text(
        "What *tone* should the post have?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=tone_keyboard("social"),
    )
    return SOC_TONE


async def social_tone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["tone"] = query.data.replace("tone:", "")
    await query.edit_message_text(
        "What is the *call to action*?\n\n_e.g. 'DM us to book', 'Call 0801234567', 'Visit our website'_\n\n_(Type 'skip' for none)_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return SOC_CTA


async def social_cta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    val = update.message.text.strip()
    context.user_data["cta"] = "" if val.lower() == "skip" else val
    await update.message.reply_text(
        f"✅ Generating *3 post variations* for {context.user_data.get('platform', '').replace('_', ' ').title()}...",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=confirm_keyboard("social"),
    )
    return SOC_CONFIRM


async def social_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "confirm:cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Cancelled.", reply_markup=back_to_main_keyboard())
        return ConversationHandler.END

    await query.edit_message_text("⏳ Writing your posts...")

    tg_id   = update.effective_user.id
    user    = await get_user_by_telegram_id(tg_id)
    profile = await get_business_profile(tg_id)

    user_input = {
        **context.user_data,
        "business_name":   profile.get("business_name", user.get("full_name", "")),
        "target_audience": "Nigerian customers",
        "include_hashtags": True,
        "key_message":     context.user_data.get("product_or_service", ""),
    }

    result = await generate_document(DocType.SOCIAL_POST, user_input, profile)
    if not result["success"]:
        await query.edit_message_text("⚠️ Generation failed.", reply_markup=back_to_main_keyboard())
        return ConversationHandler.END

    await _deliver_document(update, DocType.SOCIAL_POST, result, user, user_input)
    context.user_data.clear()
    return ConversationHandler.END


def build_social_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("post", social_start),
            CallbackQueryHandler(social_start, pattern="^doc:social_post$"),
        ],
        states={
            SOC_PLATFORM: [CallbackQueryHandler(social_platform, pattern="^platform:")],
            SOC_PRODUCT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, social_product)],
            SOC_TONE:     [CallbackQueryHandler(social_tone, pattern="^tone:")],
            SOC_CTA:      [MessageHandler(filters.TEXT & ~filters.COMMAND, social_cta)],
            SOC_CONFIRM:  [CallbackQueryHandler(social_confirm, pattern="^confirm:")],
        },
        fallbacks=[CommandHandler("cancel", _cancel)],
        allow_reentry=True,
    )


# ════════════════════════════════════════════════════════════════
# CUSTOMER REPLY
# ════════════════════════════════════════════════════════════════

async def reply_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _check_and_warn(update):
        return ConversationHandler.END
    context.user_data.clear()

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "💬 *Customer Reply Assistant*\n\nPaste the *customer's message* you need to respond to:",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await update.message.reply_text(
            "💬 *Customer Reply Assistant*\n\nPaste the *customer's message* you need to respond to:",
            parse_mode=ParseMode.MARKDOWN,
        )
    return REPLY_CONTEXT


async def reply_context(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["customer_message"] = update.message.text.strip()
    await update.message.reply_text(
        "What *resolution* are you offering?\n\n_e.g. 'Full refund', 'Replacement', 'Delivery by Friday', 'Apology only'_\n\n_(Type 'skip' if unsure)_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return REPLY_ISSUE


async def reply_issue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    val = update.message.text.strip()
    context.user_data["resolution_offered"] = "" if val.lower() == "skip" else val
    await update.message.reply_text(
        "What *tone* should the reply have?",
        reply_markup=tone_keyboard("reply"),
    )
    return REPLY_TONE


async def reply_tone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["tone"] = query.data.replace("tone:", "")
    await query.edit_message_text("⏳ Drafting your reply...")

    tg_id   = update.effective_user.id
    user    = await get_user_by_telegram_id(tg_id)
    profile = await get_business_profile(tg_id)

    user_input = {
        **context.user_data,
        "business_name": profile.get("business_name", user.get("full_name", "")),
        "channel": "WhatsApp",
        "issue_type": "complaint",
    }

    result = await generate_document(DocType.REPLY, user_input, profile)
    if not result["success"]:
        await query.edit_message_text("⚠️ Generation failed.", reply_markup=back_to_main_keyboard())
        return ConversationHandler.END

    await _deliver_document(update, DocType.REPLY, result, user, user_input)
    context.user_data.clear()
    return ConversationHandler.END


def build_reply_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("reply", reply_start),
            CallbackQueryHandler(reply_start, pattern="^doc:reply$"),
        ],
        states={
            REPLY_CONTEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, reply_context)],
            REPLY_ISSUE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, reply_issue)],
            REPLY_TONE:    [CallbackQueryHandler(reply_tone, pattern="^tone:")],
        },
        fallbacks=[CommandHandler("cancel", _cancel)],
        allow_reentry=True,
    )


# ════════════════════════════════════════════════════════════════
# BUSINESS PLAN SUMMARY
# ════════════════════════════════════════════════════════════════

async def bizplan_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _check_and_warn(update):
        return ConversationHandler.END
    context.user_data.clear()

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "📊 *Business Plan Summary*\n\nDescribe your business in 2–3 sentences:",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await update.message.reply_text(
            "📊 *Business Plan Summary*\n\nDescribe your business in 2–3 sentences:",
            parse_mode=ParseMode.MARKDOWN,
        )
    return BIZPLAN_DESC


async def bizplan_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["business_description"] = update.message.text.strip()
    await update.message.reply_text(
        "Who is your *target market*?\n\n_e.g. 'Lagos-based restaurants and hotels', 'SME owners in Abuja'_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return BIZPLAN_MARKET


async def bizplan_market(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["target_market"] = update.message.text.strip()
    await update.message.reply_text(
        "Enter these financial estimates (one per line):\n\n"
        "`Monthly Revenue | Monthly Expenses | Startup Cost`\n\n"
        "_Example:_\n"
        "`500000 | 200000 | 1500000`",
        parse_mode=ParseMode.MARKDOWN,
    )
    return BIZPLAN_REVENUE


async def bizplan_revenue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    parts = [p.strip().replace(",", "").replace("₦", "") for p in update.message.text.split("|")]
    try:
        context.user_data["monthly_revenue_estimate"] = float(parts[0]) if parts else 0
        context.user_data["monthly_expenses"]         = float(parts[1]) if len(parts) > 1 else 0
        context.user_data["startup_costs"]            = float(parts[2]) if len(parts) > 2 else 0
    except (ValueError, IndexError):
        context.user_data["monthly_revenue_estimate"] = 0
        context.user_data["startup_costs"]            = 0

    await update.message.reply_text(
        "What is the *purpose* of this business plan?\n\n"
        "_e.g. 'BOI loan application', 'Bank loan', 'Investor pitch', 'Internal planning'_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return BIZPLAN_PURPOSE


async def bizplan_purpose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["loan_purpose"] = update.message.text.strip()
    await update.message.reply_text("⏳ Writing your business plan...", reply_markup=confirm_keyboard("bizplan"))
    return BIZPLAN_CONFIRM


async def bizplan_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "confirm:cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Cancelled.", reply_markup=back_to_main_keyboard())
        return ConversationHandler.END

    await query.edit_message_text("⏳ Writing your business plan summary...")

    tg_id   = update.effective_user.id
    user    = await get_user_by_telegram_id(tg_id)
    profile = await get_business_profile(tg_id)

    user_input = {
        **context.user_data,
        "business_name":        profile.get("business_name", user.get("full_name", "")),
        "products_services":    context.user_data.get("business_description", ""),
        "revenue_model":        "Direct sales and service contracts",
        "competitive_advantage": "Quality, reliability, and local market expertise",
    }

    result = await generate_document(DocType.BUSINESS_PLAN, user_input, profile)
    if not result["success"]:
        await query.edit_message_text("⚠️ Generation failed.", reply_markup=back_to_main_keyboard())
        return ConversationHandler.END

    await _deliver_document(update, DocType.BUSINESS_PLAN, result, user, user_input)
    context.user_data.clear()
    return ConversationHandler.END


def build_bizplan_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("bizplan", bizplan_start),
            CallbackQueryHandler(bizplan_start, pattern="^doc:business_plan$"),
        ],
        states={
            BIZPLAN_DESC:    [MessageHandler(filters.TEXT & ~filters.COMMAND, bizplan_desc)],
            BIZPLAN_MARKET:  [MessageHandler(filters.TEXT & ~filters.COMMAND, bizplan_market)],
            BIZPLAN_REVENUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bizplan_revenue)],
            BIZPLAN_PURPOSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bizplan_purpose)],
            BIZPLAN_CONFIRM: [CallbackQueryHandler(bizplan_confirm, pattern="^confirm:")],
        },
        fallbacks=[CommandHandler("cancel", _cancel)],
        allow_reentry=True,
    )


# ════════════════════════════════════════════════════════════════
# VOICE MESSAGE HANDLER
# ════════════════════════════════════════════════════════════════

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Transcribe incoming voice notes using Whisper, classify via Claude,
    and route to the matching document flow with pre-filled data.
    """
    msg = await update.message.reply_text("Transcribing your voice note...")

    voice = update.message.voice
    file  = await context.bot.get_file(voice.file_id)

    import io as _io
    buf = _io.BytesIO()
    await file.download_to_memory(buf)
    audio_bytes = buf.getvalue()

    transcript = await transcribe_voice(audio_bytes, file_ext="ogg")

    if not transcript:
        await msg.edit_text(
            "Could not transcribe your voice note.\n\n"
            "Please type your request or use a command from /help.",
            reply_markup=back_to_main_keyboard(),
        )
        return

    context.user_data["voice_transcript"] = transcript

    from app.services.ai.prompts import build_voice_classification_prompt
    from app.services.ai.claude_client import get_claude_client, _parse_json_response
    from app.core.config import settings as _settings

    try:
        client = get_claude_client()
        sys_prompt, user_prompt = build_voice_classification_prompt(transcript)
        response = await client.messages.create(
            model=_settings.claude_model,
            max_tokens=500,
            system=sys_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        classification = _parse_json_response(response.content[0].text.strip())
    except Exception:
        classification = None

    from app.bot.keyboards.menus import main_menu_keyboard

    if not classification or not classification.get("doc_type") or classification.get("confidence", 0) < 0.5:
        await msg.edit_text(
            f"*I heard:*\n_{transcript}_\n\n"
            f"I couldn't determine the document type. Please pick one:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard(),
        )
        return

    doc_type = classification["doc_type"]
    extracted = classification.get("extracted_data", {})
    summary = classification.get("summary", "")

    context.user_data.update(extracted)

    doc_labels = {
        "invoice": "Invoice", "proposal": "Business Proposal",
        "contract": "Contract", "social_post": "Social Media Content",
        "reply": "Customer Reply", "business_plan": "Business Plan",
    }
    label = doc_labels.get(doc_type, doc_type)

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    await msg.edit_text(
        f"*I heard:*\n_{transcript}_\n\n"
        f"Detected: *{label}*\n{summary}\n\n"
        f"Tap below to start or pick a different type:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"Create {label}", callback_data=f"doc:{doc_type}")],
            [InlineKeyboardButton("Pick another type", callback_data="menu:main")],
        ]),
    )
