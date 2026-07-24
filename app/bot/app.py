"""
app/bot/app.py
---------------
Builds and returns the fully configured Telegram Application.

All ConversationHandlers, CommandHandlers, and CallbackQueryHandlers
are registered here in the correct priority order.

Usage:
    from app.bot.app import build_bot_app
    telegram_app = build_bot_app()
"""

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from loguru import logger

from app.core.config import settings
from app.bot.handlers.common import (
    build_onboarding_handler,
    build_profile_update_handler,
    help_handler,
    cancel_handler,
    profile_handler,
    upgrade_handler,
    upgrade_callback,
    history_handler,
    menu_callback,
)
from app.bot.handlers.invoice import build_invoice_handler
from app.bot.handlers.documents import (
    build_proposal_handler,
    build_contract_handler,
    build_social_handler,
    build_reply_handler,
    build_bizplan_handler,
    voice_handler,
)
from app.bot.handlers.expenses import (
    build_expense_handler,
    scan_command,
    photo_handler,
    try_quick_expense,
)
from app.bot.handlers.dashboard import build_dashboard_handler
from app.bot.handlers.tax import (
    tax_command,
    tax_current_month,
    tax_quarter,
    tax_deadlines,
    tax_save_record,
    tax_menu_back,
)
from app.bot.handlers.team import build_team_handler
from app.bot.handlers.language import language_command, language_selected
from app.bot.handlers.insights import (
    insights_command,
    insights_monthly,
    insights_trends,
    insights_anomalies,
    insights_menu_back,
)


def build_bot_app() -> Application:
    """
    Construct the fully wired Telegram Application.

    ConversationHandlers MUST be registered before generic
    CallbackQueryHandlers, otherwise button callbacks inside
    conversations won't be routed correctly.
    """
    app = Application.builder().token(settings.telegram_bot_token).build()

    # ── Conversation handlers (highest priority) ──────────────────
    app.add_handler(build_onboarding_handler())
    app.add_handler(build_profile_update_handler())
    app.add_handler(build_expense_handler())
    app.add_handler(build_dashboard_handler())
    app.add_handler(build_invoice_handler())
    app.add_handler(build_proposal_handler())
    app.add_handler(build_contract_handler())
    app.add_handler(build_social_handler())
    app.add_handler(build_reply_handler())
    app.add_handler(build_bizplan_handler())
    app.add_handler(build_team_handler())

    # ── Simple command handlers ───────────────────────────────────
    app.add_handler(CommandHandler("help",      help_handler))
    app.add_handler(CommandHandler("profile",   profile_handler))
    app.add_handler(CommandHandler("upgrade",   upgrade_handler))
    app.add_handler(CommandHandler("history",   history_handler))
    app.add_handler(CommandHandler("cancel",    cancel_handler))
    app.add_handler(CommandHandler("scan",      scan_command))
    app.add_handler(CommandHandler("tax",       tax_command))
    app.add_handler(CommandHandler("insights",  insights_command))
    app.add_handler(CommandHandler("language",  language_command))

    # ── Callback query routers ────────────────────────────────────
    app.add_handler(CallbackQueryHandler(upgrade_callback, pattern="^upgrade:(pro|business|commander)$"))
    app.add_handler(CallbackQueryHandler(menu_callback,    pattern="^menu:"))
    app.add_handler(CallbackQueryHandler(tax_current_month, pattern="^tax:current$"))
    app.add_handler(CallbackQueryHandler(tax_quarter,      pattern="^tax:quarter$"))
    app.add_handler(CallbackQueryHandler(tax_deadlines,    pattern="^tax:deadlines$"))
    app.add_handler(CallbackQueryHandler(tax_save_record,  pattern="^tax:save:"))
    app.add_handler(CallbackQueryHandler(tax_menu_back,    pattern="^tax:menu$"))

    # Insights callbacks
    app.add_handler(CallbackQueryHandler(insights_command,   pattern="^action:insights$"))
    app.add_handler(CallbackQueryHandler(insights_monthly,   pattern="^insights:monthly$"))
    app.add_handler(CallbackQueryHandler(insights_trends,    pattern="^insights:trends$"))
    app.add_handler(CallbackQueryHandler(insights_anomalies, pattern="^insights:anomalies$"))
    app.add_handler(CallbackQueryHandler(insights_menu_back, pattern="^insights:menu$"))

    # Language callbacks
    app.add_handler(CallbackQueryHandler(language_selected, pattern="^lang:"))

    # ── Photo handler (receipt OCR) ───────────────────────────────
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    # ── Voice message handler ─────────────────────────────────────
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))

    # ── Fallback for unknown text ─────────────────────────────────
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _unknown_text))

    logger.info("Telegram bot application built with all handlers registered")
    return app


async def _unknown_text(update, context) -> None:
    """Catch-all: try quick expense parsing first, then show menu."""
    text = update.message.text.strip() if update.message.text else ""
    if text:
        handled = await try_quick_expense(text, update, context)
        if handled:
            return

    from app.bot.keyboards.menus import main_menu_keyboard
    await update.message.reply_text(
        "I'm not sure what you mean. Use the menu below or type /help.",
        reply_markup=main_menu_keyboard(),
    )
