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
    app.add_handler(build_invoice_handler())
    app.add_handler(build_proposal_handler())
    app.add_handler(build_contract_handler())
    app.add_handler(build_social_handler())
    app.add_handler(build_reply_handler())
    app.add_handler(build_bizplan_handler())

    # ── Simple command handlers ───────────────────────────────────
    app.add_handler(CommandHandler("help",    help_handler))
    app.add_handler(CommandHandler("profile", profile_handler))
    app.add_handler(CommandHandler("upgrade", upgrade_handler))
    app.add_handler(CommandHandler("history", history_handler))
    app.add_handler(CommandHandler("cancel",  cancel_handler))

    # ── Callback query routers ────────────────────────────────────
    app.add_handler(CallbackQueryHandler(upgrade_callback, pattern="^upgrade:"))
    app.add_handler(CallbackQueryHandler(menu_callback,    pattern="^menu:"))

    # ── Voice message handler ─────────────────────────────────────
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))

    # ── Fallback for unknown text ─────────────────────────────────
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _unknown_text))

    logger.info("Telegram bot application built with all handlers registered")
    return app


async def _unknown_text(update, context) -> None:
    """Catch-all for messages not captured by any ConversationHandler."""
    from app.bot.keyboards.menus import main_menu_keyboard
    from telegram.constants import ParseMode
    await update.message.reply_text(
        "I'm not sure what you mean. Use the menu below or type /help.",
        reply_markup=main_menu_keyboard(),
    )
