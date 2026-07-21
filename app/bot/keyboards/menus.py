"""
app/bot/keyboards/menus.py
---------------------------
All InlineKeyboardMarkup and ReplyKeyboardMarkup definitions.

Keeping keyboards in one file means changing a button label
only ever requires editing one place.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from app.core.constants import (
    DocType,
    NIGERIAN_BUSINESS_TYPES,
    SocialPlatform,
    SubscriptionTier,
)


# ── Main Menu ────────────────────────────────────────────────────────────────

def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📄 Invoice",        callback_data="doc:invoice"),
            InlineKeyboardButton("📋 Proposal",       callback_data="doc:proposal"),
        ],
        [
            InlineKeyboardButton("📝 Contract",       callback_data="doc:contract"),
            InlineKeyboardButton("📱 Social Post",    callback_data="doc:social_post"),
        ],
        [
            InlineKeyboardButton("💬 Customer Reply", callback_data="doc:reply"),
            InlineKeyboardButton("📊 Business Plan",  callback_data="doc:business_plan"),
        ],
        [
            InlineKeyboardButton("⚙️ My Profile",     callback_data="menu:profile"),
            InlineKeyboardButton("💳 Upgrade",        callback_data="menu:upgrade"),
        ],
        [
            InlineKeyboardButton("📂 My Documents",   callback_data="menu:history"),
        ],
    ])


# ── Business Type Selection ──────────────────────────────────────────────────

def business_type_keyboard() -> InlineKeyboardMarkup:
    """Paginated list of Nigerian business types."""
    rows = []
    types = NIGERIAN_BUSINESS_TYPES
    # Two buttons per row
    for i in range(0, len(types), 2):
        row = [InlineKeyboardButton(types[i], callback_data=f"biztype:{types[i]}")]
        if i + 1 < len(types):
            row.append(InlineKeyboardButton(types[i + 1], callback_data=f"biztype:{types[i + 1]}"))
        rows.append(row)
    return InlineKeyboardMarkup(rows)


# ── Payment Terms ────────────────────────────────────────────────────────────

def payment_terms_keyboard() -> InlineKeyboardMarkup:
    terms = ["Net 7", "Net 14", "Net 30", "Due on Receipt", "50% Upfront", "Custom"]
    rows = []
    for i in range(0, len(terms), 2):
        row = [InlineKeyboardButton(terms[i], callback_data=f"terms:{terms[i]}")]
        if i + 1 < len(terms):
            row.append(InlineKeyboardButton(terms[i + 1], callback_data=f"terms:{terms[i + 1]}"))
        rows.append(row)
    return InlineKeyboardMarkup(rows)


# ── Contract Types ───────────────────────────────────────────────────────────

def contract_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋 Service Agreement", callback_data="conttype:service_agreement"),
            InlineKeyboardButton("🔒 NDA",               callback_data="conttype:nda"),
        ],
        [
            InlineKeyboardButton("🤝 Vendor Agreement",  callback_data="conttype:vendor_agreement"),
            InlineKeyboardButton("💼 Partnership",        callback_data="conttype:partnership"),
        ],
    ])


# ── Social Platform ──────────────────────────────────────────────────────────

def social_platform_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📸 Instagram",       callback_data="platform:instagram"),
            InlineKeyboardButton("👥 Facebook",        callback_data="platform:facebook"),
        ],
        [
            InlineKeyboardButton("🐦 X (Twitter)",     callback_data="platform:twitter_x"),
            InlineKeyboardButton("💚 WhatsApp",        callback_data="platform:whatsapp"),
        ],
        [
            InlineKeyboardButton("💼 LinkedIn",        callback_data="platform:linkedin"),
            InlineKeyboardButton("🎵 TikTok",          callback_data="platform:tiktok"),
        ],
    ])


# ── Tone Selection ───────────────────────────────────────────────────────────

def tone_keyboard(context: str = "social") -> InlineKeyboardMarkup:
    """context: 'social' | 'reply'"""
    if context == "social":
        tones = [
            ("🔥 Bold & Energetic",    "bold"),
            ("😊 Friendly & Warm",     "friendly"),
            ("💼 Professional",        "professional"),
            ("😂 Funny & Relatable",   "funny"),
            ("✨ Inspirational",       "inspirational"),
            ("📢 Urgent/Promotional",  "urgent"),
        ]
    else:
        tones = [
            ("😊 Empathetic",          "empathetic"),
            ("💼 Formal",              "formal"),
            ("🤝 Apologetic",          "apologetic"),
            ("✅ Solution-focused",    "solution"),
        ]
    rows = []
    for i in range(0, len(tones), 2):
        row = [InlineKeyboardButton(tones[i][0], callback_data=f"tone:{tones[i][1]}")]
        if i + 1 < len(tones):
            row.append(InlineKeyboardButton(tones[i + 1][0], callback_data=f"tone:{tones[i + 1][1]}"))
        rows.append(row)
    return InlineKeyboardMarkup(rows)


# ── Output Format ────────────────────────────────────────────────────────────

def output_format_keyboard(is_free: bool = True) -> InlineKeyboardMarkup:
    if is_free:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📄 Preview in Chat (Free)", callback_data="fmt:text")],
            [InlineKeyboardButton("⬆️ Upgrade for PDF/DOCX",   callback_data="menu:upgrade")],
        ])
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📄 PDF",    callback_data="fmt:pdf"),
            InlineKeyboardButton("📝 DOCX",   callback_data="fmt:docx"),
            InlineKeyboardButton("💬 In Chat", callback_data="fmt:text"),
        ],
    ])


# ── Confirmation ─────────────────────────────────────────────────────────────

def confirm_keyboard(action: str = "generate") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Generate Document", callback_data=f"confirm:{action}"),
            InlineKeyboardButton("✏️ Edit Details",      callback_data="confirm:edit"),
        ],
        [
            InlineKeyboardButton("❌ Cancel",            callback_data="confirm:cancel"),
        ],
    ])


# ── Upgrade / Subscription ───────────────────────────────────────────────────

def upgrade_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Pro — ₦4,999/month",        callback_data="upgrade:pro")],
        [InlineKeyboardButton("🏆 Commander — ₦12,999/month", callback_data="upgrade:commander")],
        [InlineKeyboardButton("🔙 Back to Menu",              callback_data="menu:main")],
    ])


# ── Document History Actions ─────────────────────────────────────────────────

def history_action_keyboard(doc_id: str, file_url: str | None) -> InlineKeyboardMarkup:
    rows = []
    if file_url:
        rows.append([InlineKeyboardButton("📥 Download Again", url=file_url)])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="menu:history")])
    return InlineKeyboardMarkup(rows)


# ── Yes / No ─────────────────────────────────────────────────────────────────

def yes_no_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes", callback_data=yes_data),
            InlineKeyboardButton("❌ No",  callback_data=no_data),
        ]
    ])


# ── Profile Update Field Selection ───────────────────────────────────────────

def profile_field_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏢 Business Name", callback_data="pfield:business_name"),
            InlineKeyboardButton("🏭 Business Type", callback_data="pfield:business_type"),
        ],
        [
            InlineKeyboardButton("🏦 Bank Name",     callback_data="pfield:bank_name"),
            InlineKeyboardButton("💳 Account No.",    callback_data="pfield:account_number"),
        ],
        [
            InlineKeyboardButton("👤 Account Name",  callback_data="pfield:account_name"),
            InlineKeyboardButton("📋 CAC Number",    callback_data="pfield:cac_number"),
        ],
        [
            InlineKeyboardButton("🔑 TIN Number",    callback_data="pfield:tin_number"),
        ],
        [
            InlineKeyboardButton("🔙 Back to Profile", callback_data="menu:profile"),
        ],
    ])


# ── Back to Main ─────────────────────────────────────────────────────────────

def back_to_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu:main")],
    ])
