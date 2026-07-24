"""
app/bot/handlers/language.py
-------------------------------
Language selection:
  /language — Switch between English, Pidgin, Yoruba, Hausa
"""

from __future__ import annotations

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from app.core.i18n import SUPPORTED_LANGUAGES, t, get_user_lang
from app.db.client import get_user_by_telegram_id, update_user_profile
from app.bot.keyboards.menus import back_to_main_keyboard


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show language selection menu."""
    buttons = []
    for code, name in SUPPORTED_LANGUAGES.items():
        flag = {"en": "🇬🇧", "pcm": "🇳🇬", "yo": "🇳🇬", "ha": "🇳🇬"}.get(code, "🌍")
        buttons.append(
            [InlineKeyboardButton(f"{flag} {name}", callback_data=f"lang:{code}")]
        )
    buttons.append([InlineKeyboardButton("Cancel", callback_data="menu:main")])

    user = await get_user_by_telegram_id(update.effective_user.id)
    lang = get_user_lang(user)

    await _send(update,
        t("language_select", lang=lang),
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def language_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle language selection callback."""
    query = update.callback_query
    await query.answer()

    lang_code = query.data.replace("lang:", "")
    if lang_code not in SUPPORTED_LANGUAGES:
        return

    tg_id = update.effective_user.id
    await update_user_profile(tg_id, {"language": lang_code})

    lang_name = SUPPORTED_LANGUAGES[lang_code]
    await query.edit_message_text(
        t("language_changed", lang=lang_code),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_to_main_keyboard(),
    )


async def _send(update: Update, text: str, reply_markup=None) -> None:
    kwargs = {"text": text, "parse_mode": ParseMode.MARKDOWN}
    if reply_markup:
        kwargs["reply_markup"] = reply_markup
    if update.callback_query:
        await update.callback_query.edit_message_text(**kwargs)
    else:
        await update.message.reply_text(**kwargs)
