"""
app/bot/handlers/common.py
---------------------------
Handlers for:
  /start     — Welcome + onboarding flow
  /help      — Command menu
  /profile   — View/update business profile
  /history   — Recent documents
  /upgrade   — Subscription plans
  /cancel    — Cancel current flow
  menu:*     — Inline keyboard navigation callbacks
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

from app.core.constants import (
    WELCOME_MESSAGE,
    HELP_MESSAGE,
    UPGRADE_MESSAGE,
    ONBOARD_NAME,
    ONBOARD_BIZ_NAME,
    ONBOARD_BIZ_TYPE,
    PROFILE_FIELD,
    PROFILE_VALUE,
    DOC_TYPE_LABELS,
    SubscriptionTier,
)
from app.bot.keyboards.menus import (
    main_menu_keyboard,
    business_type_keyboard,
    upgrade_keyboard,
    back_to_main_keyboard,
    history_action_keyboard,
    profile_field_keyboard,
)
from app.db.client import (
    get_or_create_user,
    get_user_by_telegram_id,
    update_user_profile,
    get_user_documents,
    get_business_profile,
    save_business_profile,
)


# ── /start ───────────────────────────────────────────────────────────────────

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point. Creates user if new, shows onboarding or main menu."""
    tg_user = update.effective_user
    user, is_new = await get_or_create_user(
        telegram_id=tg_user.id,
        full_name=tg_user.full_name,
        username=tg_user.username,
    )

    if is_new:
        await update.message.reply_text(
            "👋 Welcome to *BizPilot NG* — Your AI Business Assistant!\n\n"
            "I'll help you create professional Nigerian business documents in seconds.\n\n"
            "Let's set up your profile quickly. What's your *full name*?",
            parse_mode=ParseMode.MARKDOWN,
        )
        return ONBOARD_NAME

    # Returning user — show main menu
    await update.message.reply_text(
        f"Welcome back, *{user['full_name']}*! 👋\n\nWhat would you like to create today?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def onboard_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    context.user_data["onboard_name"] = name
    await update_user_profile(update.effective_user.id, {"full_name": name})

    await update.message.reply_text(
        f"Nice to meet you, *{name}*! 🎉\n\nWhat is your *business name*?",
        parse_mode=ParseMode.MARKDOWN,
    )
    return ONBOARD_BIZ_NAME


async def onboard_biz_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    biz_name = update.message.text.strip()
    context.user_data["onboard_biz_name"] = biz_name

    await update.message.reply_text(
        f"Great! *{biz_name}* — love it! 💼\n\nWhat type of business is it?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=business_type_keyboard(),
    )
    return ONBOARD_BIZ_TYPE


async def onboard_biz_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the business type button tap."""
    query = update.callback_query
    await query.answer()

    biz_type = query.data.replace("biztype:", "")
    tg_id    = update.effective_user.id

    profile = {
        "business_name": context.user_data.get("onboard_biz_name", ""),
        "business_type": biz_type,
    }
    await save_business_profile(tg_id, profile)

    await query.edit_message_text(
        f"✅ Profile saved!\n\n"
        f"*Business:* {profile['business_name']}\n"
        f"*Type:* {biz_type}\n\n"
        f"You have *5 free documents* this month. What would you like to create?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(),
    )

    user = await get_user_by_telegram_id(tg_id)
    email = user.get("email") if user else None
    if email:
        from app.services.payments.email import send_welcome_email
        name = context.user_data.get("onboard_name", "there")
        await send_welcome_email(email, name)

    return ConversationHandler.END


# ── /help ────────────────────────────────────────────────────────────────────

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        HELP_MESSAGE,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(),
    )


# ── /cancel ──────────────────────────────────────────────────────────────────

async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Operation cancelled.\n\nWhat would you like to do?",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


# ── /profile ─────────────────────────────────────────────────────────────────

async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_id   = update.effective_user.id
    user    = await get_user_by_telegram_id(tg_id)
    profile = await get_business_profile(tg_id)

    if not user:
        await update.message.reply_text("Please /start first.")
        return

    tier_label = {
        SubscriptionTier.FREE:       "🆓 Starter (Free)",
        SubscriptionTier.PRO:        "⚡ Pro Operator",
        SubscriptionTier.COMMANDER:  "🏆 Business Commander",
    }.get(user.get("subscription", "free"), "Free")

    expires = user.get("sub_expires_at", "")
    expires_line = f"\n📅 *Expires:* {expires[:10]}" if expires else ""

    text = (
        f"⚙️ *Your Business Profile*\n\n"
        f"👤 *Name:* {user.get('full_name', 'Not set')}\n"
        f"🏢 *Business:* {profile.get('business_name', 'Not set')}\n"
        f"🏭 *Type:* {profile.get('business_type', 'Not set')}\n"
        f"🏦 *Bank:* {profile.get('bank_name', 'Not set')}\n"
        f"📋 *CAC:* {profile.get('cac_number', 'Not set')}\n"
        f"🔑 *TIN:* {profile.get('tin_number', 'Not set')}\n\n"
        f"💳 *Plan:* {tier_label}{expires_line}\n"
        f"📄 *Documents used:* {user.get('docs_used', 0)} / {user.get('docs_limit', 5)}"
    )

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Update Profile", callback_data="profile:update")],
        [InlineKeyboardButton("🏠 Main Menu",      callback_data="menu:main")],
    ])

    if update.message:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    else:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


# ── /upgrade ─────────────────────────────────────────────────────────────────

async def upgrade_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            UPGRADE_MESSAGE,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=upgrade_keyboard(),
        )
    else:
        await update.callback_query.edit_message_text(
            UPGRADE_MESSAGE,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=upgrade_keyboard(),
        )


async def upgrade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles upgrade:pro and upgrade:business button taps."""
    query = update.callback_query
    await query.answer()

    tier_key = query.data.replace("upgrade:", "")
    tier_map = {"pro": SubscriptionTier.PRO, "business": SubscriptionTier.BUSINESS, "commander": SubscriptionTier.BUSINESS}
    tier = tier_map.get(tier_key, SubscriptionTier.PRO)

    tg_id = update.effective_user.id
    user  = await get_user_by_telegram_id(tg_id)
    if not user:
        await query.edit_message_text("Please /start first.")
        return

    from app.services.payments.paystack import initialize_subscription, get_plan_code
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    plan_code = get_plan_code(tier)
    if not plan_code:
        await query.edit_message_text(
            "⚠️ Payment plans are not configured yet. Please contact support.",
            reply_markup=back_to_main_keyboard(),
        )
        return

    email = user.get("email") or f"{tg_id}@bizpilot.ng"
    result = await initialize_subscription(
        email=email,
        plan_code=plan_code,
        telegram_id=tg_id,
        tier=tier,
    )

    if not result:
        await query.edit_message_text(
            "⚠️ Payment initialisation failed. Please try again later.",
            reply_markup=back_to_main_keyboard(),
        )
        return

    plan_name = "Pro ⚡" if tier == SubscriptionTier.PRO else "Business 🏢"
    await query.edit_message_text(
        f"💳 *{plan_name} Subscription*\n\n"
        f"Tap the button below to complete payment securely via Paystack.\n\n"
        f"After payment, your plan activates automatically within 60 seconds.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Pay Now on Paystack", url=result["authorization_url"])],
            [InlineKeyboardButton("🔙 Back",               callback_data="menu:upgrade")],
        ]),
    )


# ── /history ─────────────────────────────────────────────────────────────────

async def history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_id = update.effective_user.id
    user  = await get_user_by_telegram_id(tg_id)
    if not user:
        if update.message:
            await update.message.reply_text("Please /start first.")
        return

    docs = await get_user_documents(user["id"], limit=8)

    if not docs:
        text = "📂 *Your Documents*\n\nYou haven't generated any documents yet.\n\nUse the menu below to create your first one!"
    else:
        lines = ["📂 *Your Recent Documents*\n"]
        for doc in docs:
            label    = DOC_TYPE_LABELS.get(doc["doc_type"], doc["doc_type"])
            date_str = doc["created_at"][:10]
            fmt      = doc.get("output_format", "text").upper()
            lines.append(f"• {label} — {date_str} [{fmt}]")
        text = "\n".join(lines)

    if update.message:
        await update.message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_keyboard()
        )
    else:
        await update.callback_query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_keyboard()
        )


# ── Profile Update Flow ──────────────────────────────────────────────────────

PROFILE_FIELD_LABELS = {
    "business_name":  "Business Name",
    "business_type":  "Business Type",
    "bank_name":      "Bank Name",
    "account_number": "Account Number",
    "account_name":   "Account Name",
    "cac_number":     "CAC Registration Number",
    "tin_number":     "TIN Number",
}


async def profile_update_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "✏️ *Update Profile*\n\nWhich field would you like to update?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=profile_field_keyboard(),
    )
    return PROFILE_FIELD


async def profile_field_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    field = query.data.replace("pfield:", "")
    context.user_data["profile_update_field"] = field
    label = PROFILE_FIELD_LABELS.get(field, field)

    if field == "business_type":
        await query.edit_message_text(
            f"Select your new *{label}*:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=business_type_keyboard(),
        )
        return PROFILE_VALUE

    await query.edit_message_text(
        f"Please type your new *{label}*:",
        parse_mode=ParseMode.MARKDOWN,
    )
    return PROFILE_VALUE


async def profile_value_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = update.message.text.strip()
    field = context.user_data.get("profile_update_field", "")
    label = PROFILE_FIELD_LABELS.get(field, field)
    tg_id = update.effective_user.id

    profile = await get_business_profile(tg_id)
    profile[field] = value
    await save_business_profile(tg_id, profile)

    await update.message.reply_text(
        f"✅ *{label}* updated to: {value}\n\nWould you like to update anything else?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=profile_field_keyboard(),
    )
    return PROFILE_FIELD


async def profile_value_biztype(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    biz_type = query.data.replace("biztype:", "")
    tg_id = update.effective_user.id

    profile = await get_business_profile(tg_id)
    profile["business_type"] = biz_type
    await save_business_profile(tg_id, profile)

    await query.edit_message_text(
        f"✅ *Business Type* updated to: {biz_type}\n\nWould you like to update anything else?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=profile_field_keyboard(),
    )
    return PROFILE_FIELD


async def profile_update_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await profile_handler(update, context)
    return ConversationHandler.END


def build_profile_update_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(profile_update_start, pattern="^profile:update$")],
        states={
            PROFILE_FIELD: [
                CallbackQueryHandler(profile_field_selected, pattern="^pfield:"),
                CallbackQueryHandler(profile_update_back, pattern="^menu:profile$"),
            ],
            PROFILE_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, profile_value_text),
                CallbackQueryHandler(profile_value_biztype, pattern="^biztype:"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_handler),
            CallbackQueryHandler(profile_update_back, pattern="^menu:profile$"),
        ],
        per_message=False,
    )


# ── Menu Navigation Callbacks ─────────────────────────────────────────────────

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Routes menu:* callbacks to the right handler."""
    query = update.callback_query
    await query.answer()
    action = query.data.replace("menu:", "")

    if action == "main":
        user = await get_user_by_telegram_id(update.effective_user.id)
        name = user["full_name"] if user else "there"
        await query.edit_message_text(
            f"What would you like to create, *{name}*?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard(),
        )
    elif action == "upgrade":
        await upgrade_handler(update, context)
    elif action == "profile":
        await profile_handler(update, context)
    elif action == "history":
        await history_handler(update, context)


# ── Onboarding ConversationHandler Builder ────────────────────────────────────

def build_onboarding_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("start", start_handler)],
        states={
            ONBOARD_NAME:     [MessageHandler(filters.TEXT & ~filters.COMMAND, onboard_name)],
            ONBOARD_BIZ_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboard_biz_name)],
            ONBOARD_BIZ_TYPE: [CallbackQueryHandler(onboard_biz_type, pattern="^biztype:")],
        },
        fallbacks=[CommandHandler("cancel", cancel_handler)],
        allow_reentry=True,
    )
