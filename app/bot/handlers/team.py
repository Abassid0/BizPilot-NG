"""
app/bot/handlers/team.py
--------------------------
Team management via Telegram:
  /team — Create team, invite members, manage roles
"""

from __future__ import annotations

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

from app.core.constants import TEAM_CREATE_NAME, TEAM_INVITE_ROLE
from app.bot.keyboards.menus import back_to_main_keyboard
from app.db.client import (
    get_user_by_telegram_id,
    get_user_team,
    get_team_members,
    create_team,
    create_team_invitation,
    accept_team_invitation,
    remove_team_member,
)


async def team_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show team dashboard or offer to create one."""
    tg_id = update.effective_user.id
    user = await get_user_by_telegram_id(tg_id)
    if not user:
        await _send(update, "Please /start first.")
        return ConversationHandler.END

    membership = await get_user_team(user["id"])

    if not membership:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Create Team", callback_data="team:create")],
            [InlineKeyboardButton("Join Team", callback_data="team:join")],
            [InlineKeyboardButton("Main Menu", callback_data="menu:main")],
        ])
        await _send(update,
            "*Team Management*\n\n"
            "You're not part of any team yet.\n"
            "Create a team to invite staff, accountants, or partners.",
            reply_markup=keyboard,
        )
        return TEAM_CREATE_NAME

    team = membership.get("teams", {})
    role = membership.get("role", "member")
    members = await get_team_members(team["id"])

    role_emoji = {"owner": "👑", "admin": "🔑", "member": "👤", "accountant": "📊", "viewer": "👁"}

    lines = [
        f"*Team: {team.get('name', 'My Team')}*",
        f"Your role: {role_emoji.get(role, '👤')} {role.title()}\n",
        f"*Members ({len(members)}):*",
    ]

    for m in members:
        u = m.get("users", {})
        name = u.get("full_name", "Unknown")
        r = m.get("role", "member")
        lines.append(f"  {role_emoji.get(r, '👤')} {name} — {r}")

    lines.append("")

    buttons = []
    if role in ("owner", "admin"):
        buttons.append([InlineKeyboardButton("Invite Member", callback_data="team:invite")])
        buttons.append([InlineKeyboardButton("Manage Members", callback_data="team:manage")])
    buttons.append([InlineKeyboardButton("Main Menu", callback_data="menu:main")])

    await _send(update, "\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))
    return TEAM_CREATE_NAME


async def team_create_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    user = await get_user_by_telegram_id(update.effective_user.id)
    if not user:
        return ConversationHandler.END

    existing = await get_user_team(user["id"])
    if existing:
        await query.edit_message_text("You already belong to a team.")
        return ConversationHandler.END

    await query.edit_message_text("What would you like to name your team?")
    return TEAM_CREATE_NAME


async def team_create_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive team name and create it."""
    name = update.message.text.strip()
    if not name or len(name) < 2:
        await update.message.reply_text("Please enter a valid team name (at least 2 characters).")
        return TEAM_CREATE_NAME

    tg_id = update.effective_user.id
    user = await get_user_by_telegram_id(tg_id)
    if not user:
        return ConversationHandler.END

    profile = user.get("business_profile") or {}

    team = await create_team(
        owner_id=user["id"],
        name=name,
        business_name=profile.get("business_name", ""),
    )

    if not team:
        await update.message.reply_text(
            "Could not create team. Please try again.",
            reply_markup=back_to_main_keyboard(),
        )
        return ConversationHandler.END

    await update.message.reply_text(
        f"*Team '{name}' created!* 🎉\n\n"
        f"You are the team owner.\n"
        f"Use /team to invite members.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_to_main_keyboard(),
    )
    return ConversationHandler.END


async def team_join_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Enter the invitation code you received:")
    context.user_data["team_action"] = "join"
    return TEAM_CREATE_NAME


async def team_join_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process a join code."""
    if context.user_data.get("team_action") != "join":
        return await team_create_name(update, context)

    code = update.message.text.strip()
    tg_id = update.effective_user.id
    user = await get_user_by_telegram_id(tg_id)
    if not user:
        return ConversationHandler.END

    result = await accept_team_invitation(code, user["id"])
    if not result:
        await update.message.reply_text(
            "Invalid or expired invitation code. Please check and try again.",
            reply_markup=back_to_main_keyboard(),
        )
        return ConversationHandler.END

    await update.message.reply_text(
        f"You've joined the team as *{result.get('role', 'member')}*! 🎉\n\n"
        f"Use /team to see your team.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_to_main_keyboard(),
    )
    context.user_data.pop("team_action", None)
    return ConversationHandler.END


async def team_invite_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Admin", callback_data="team:role:admin")],
        [InlineKeyboardButton("Member", callback_data="team:role:member")],
        [InlineKeyboardButton("Accountant", callback_data="team:role:accountant")],
        [InlineKeyboardButton("Viewer (Read-only)", callback_data="team:role:viewer")],
        [InlineKeyboardButton("Cancel", callback_data="menu:main")],
    ])
    await query.edit_message_text(
        "What role should the new member have?",
        reply_markup=keyboard,
    )
    return TEAM_INVITE_ROLE


async def team_invite_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    role = query.data.split(":")[-1]
    tg_id = update.effective_user.id
    user = await get_user_by_telegram_id(tg_id)
    if not user:
        return ConversationHandler.END

    membership = await get_user_team(user["id"])
    if not membership:
        await query.edit_message_text("You're not part of a team.")
        return ConversationHandler.END

    team = membership.get("teams", {})

    invitation = await create_team_invitation(
        team_id=team["id"],
        role=role,
        created_by=user["id"],
    )

    if not invitation:
        await query.edit_message_text("Could not create invitation. Try again.")
        return ConversationHandler.END

    code = invitation["invite_code"]
    await query.edit_message_text(
        f"*Invitation Created!*\n\n"
        f"Role: {role.title()}\n"
        f"Code: `{code}`\n"
        f"Expires in 72 hours.\n\n"
        f"Share this code with the person you want to invite. "
        f"They can join by typing /team and selecting 'Join Team'.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_to_main_keyboard(),
    )
    return ConversationHandler.END


async def _cancel_team(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("team_action", None)
    await update.message.reply_text("Team action cancelled.", reply_markup=back_to_main_keyboard())
    return ConversationHandler.END


def build_team_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("team", team_command),
        ],
        states={
            TEAM_CREATE_NAME: [
                CallbackQueryHandler(team_create_start, pattern="^team:create$"),
                CallbackQueryHandler(team_join_start, pattern="^team:join$"),
                CallbackQueryHandler(team_invite_start, pattern="^team:invite$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, team_join_code),
            ],
            TEAM_INVITE_ROLE: [
                CallbackQueryHandler(team_invite_role, pattern="^team:role:"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", _cancel_team),
            CallbackQueryHandler(
                lambda u, c: ConversationHandler.END,
                pattern="^menu:main$",
            ),
        ],
        allow_reentry=True,
    )


async def _send(update: Update, text: str, reply_markup=None) -> None:
    kwargs = {"text": text, "parse_mode": ParseMode.MARKDOWN}
    if reply_markup:
        kwargs["reply_markup"] = reply_markup
    if update.callback_query:
        await update.callback_query.edit_message_text(**kwargs)
    else:
        await update.message.reply_text(**kwargs)
