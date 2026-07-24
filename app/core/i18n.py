"""
app/core/i18n.py
-----------------
Lightweight internationalization for BizPilot NG.

Supports: English (en), Nigerian Pidgin (pcm), Yoruba (yo), Hausa (ha).

Usage:
    from app.core.i18n import t
    text = t("welcome", lang="pcm")  # "Welcome to BizPilot NG! We dey here for you."
"""

from __future__ import annotations

from typing import Optional

SUPPORTED_LANGUAGES = {
    "en":  "English",
    "pcm": "Pidgin",
    "yo":  "Yoruba",
    "ha":  "Hausa",
}

DEFAULT_LANG = "en"

_CATALOG: dict[str, dict[str, str]] = {

    # ── Welcome & Onboarding ──────────────────────────────────────

    "welcome": {
        "en":  "Welcome to *BizPilot NG* — Your AI Business Assistant!\n\nI help Nigerian entrepreneurs create professional documents, track expenses, and stay tax compliant.\n\nLet's set up your business profile first. What's your name?",
        "pcm": "Welcome to *BizPilot NG*! 🇳🇬\n\nI dey here to help you run your business better — documents, expenses, tax — everything.\n\nMake we set up your profile first. Wetin be your name?",
        "yo":  "Ẹ kú àbọ̀ sí *BizPilot NG*! 🇳🇬\n\nMo wà níbí láti ràn yín lọ́wọ́ pẹ̀lú iṣẹ́ ọ̀nà — àwọn ìwé, ìnáwó, àti owó-orí.\n\nẸ jẹ́ ká ṣètò àkọ́lé iṣẹ́ yín. Kí ni orúkọ yín?",
        "ha":  "Barka da zuwa *BizPilot NG*! 🇳🇬\n\nIna nan don taimaka muku da harkokin kasuwanci — takaddun aiki, kudade, da haraji.\n\nBari mu fara saita bayanin ku. Menene sunan ku?",
    },

    "welcome_back": {
        "en":  "Welcome back! What can I help you with today?",
        "pcm": "Welcome back! Wetin I fit help you with today?",
        "yo":  "Ẹ kú àbọ̀! Kí ni mo lè ṣe fún yín lónìí?",
        "ha":  "Barka da dawowa! Me zan iya taimaka muku yau?",
    },

    # ── Common Actions ────────────────────────────────────────────

    "start_first": {
        "en":  "Please /start first to set up your account.",
        "pcm": "Abeg /start first make we set up your account.",
        "yo":  "Jọ̀wọ́ /start láti ṣètò àkọ́lé yín.",
        "ha":  "Da fatan za a /start da farko don kafa asusun ku.",
    },

    "cancelled": {
        "en":  "Operation cancelled. Use the menu below to continue.",
        "pcm": "E don cancel. Use the menu below make you continue.",
        "yo":  "A ti fagilee. Lo àtòjọ ní ìsàlẹ̀ láti tẹ̀síwájú.",
        "ha":  "An soke shi. Yi amfani da menu a kasa don ci gaba.",
    },

    "error_generic": {
        "en":  "Something went wrong. Please try again.",
        "pcm": "Something no work well. Abeg try again.",
        "yo":  "Ohun kan kò lọ dáadáa. Jọ̀wọ́ gbìyànjú lẹ́ẹ̀kan sí.",
        "ha":  "Wani abu ya yi kuskure. Da fatan za a sake gwadawa.",
    },

    # ── Expense Tracking ──────────────────────────────────────────

    "expense_logged": {
        "en":  "Expense logged successfully!",
        "pcm": "Expense don enter! ✅",
        "yo":  "Ìnáwó ti gba sínú! ✅",
        "ha":  "An rubuta kudaden! ✅",
    },

    "expense_amount_prompt": {
        "en":  "How much did you spend? (Enter the amount in Naira)",
        "pcm": "How much you spend? (Type the amount for Naira)",
        "yo":  "Ẹ ná owó mélòó? (Ẹ tẹ iye owó ní Naira)",
        "ha":  "Nawa kuka kashe? (Shigar da adadin a cikin Naira)",
    },

    "expense_category_prompt": {
        "en":  "Select a category for this expense:",
        "pcm": "Pick category for this expense:",
        "yo":  "Yan ẹ̀ka fún ìnáwó yìí:",
        "ha":  "Zabi rukunin wannan kudade:",
    },

    # ── Dashboard ─────────────────────────────────────────────────

    "dashboard_title": {
        "en":  "Financial Dashboard",
        "pcm": "Money Dashboard",
        "yo":  "Àtẹ Owó",
        "ha":  "Shafin Kuɗi",
    },

    "income_label": {
        "en":  "Income",
        "pcm": "Money wey enter",
        "yo":  "Owó Tí Ń Wọlé",
        "ha":  "Kudin Shiga",
    },

    "expenses_label": {
        "en":  "Expenses",
        "pcm": "Money wey comot",
        "yo":  "Ìnáwó",
        "ha":  "Kudade",
    },

    "net_profit": {
        "en":  "Net Profit",
        "pcm": "Gain",
        "yo":  "Èrè Àlẹ̀",
        "ha":  "Ribar Tsarki",
    },

    "net_loss": {
        "en":  "Net Loss",
        "pcm": "Loss",
        "yo":  "Àdánù Àlẹ̀",
        "ha":  "Asara",
    },

    # ── Tax ────────────────────────────────────────────────────────

    "tax_title": {
        "en":  "Tax Compliance",
        "pcm": "Tax Matter",
        "yo":  "Ọ̀ràn Owó-Orí",
        "ha":  "Al'amuran Haraji",
    },

    "tax_reminder": {
        "en":  "VAT/WHT returns are due on the 21st. Don't forget to file!",
        "pcm": "VAT/WHT return dey due on the 21st. No forget to file am!",
        "yo":  "VAT/WHT gbọdọ̀ ṣe ní ọjọ́ 21. Má gbàgbé!",
        "ha":  "Ranar 21 ce za a biya VAT/WHT. Kada ku manta!",
    },

    # ── Insights ──────────────────────────────────────────────────

    "insights_title": {
        "en":  "Business Insights",
        "pcm": "Business Gist",
        "yo":  "Àwọn Ìmọ̀ Iṣẹ́",
        "ha":  "Fahimtar Kasuwanci",
    },

    # ── Team ──────────────────────────────────────────────────────

    "team_title": {
        "en":  "Team Management",
        "pcm": "Team Matter",
        "yo":  "Ìṣàkóso Ẹgbẹ́",
        "ha":  "Gudanar da Ƙungiya",
    },

    "team_created": {
        "en":  "Team created successfully!",
        "pcm": "Team don create! 🎉",
        "yo":  "Ẹgbẹ́ ti dá sílẹ̀! 🎉",
        "ha":  "An kirkiri ƙungiya! 🎉",
    },

    # ── Language ──────────────────────────────────────────────────

    "language_select": {
        "en":  "Choose your preferred language:",
        "pcm": "Pick the language wey you want:",
        "yo":  "Yan èdè tí ẹ fẹ́ ràn:",
        "ha":  "Zabi harshen da kuke so:",
    },

    "language_changed": {
        "en":  "Language updated to English.",
        "pcm": "Language don change to Pidgin.",
        "yo":  "Èdè ti yí padà sí Yorùbá.",
        "ha":  "An canza harshe zuwa Hausa.",
    },

    # ── Upgrade ───────────────────────────────────────────────────

    "upgrade_prompt": {
        "en":  "Upgrade your plan to unlock more features!",
        "pcm": "Upgrade your plan make you get more features!",
        "yo":  "Ṣe ìgbéga ètò yín láti ṣí àwọn ẹ̀yà tuntun!",
        "ha":  "Inganta shirinku don buɗe ƙarin fasaloli!",
    },

    "limit_reached": {
        "en":  "You've reached your monthly limit. Upgrade to continue!",
        "pcm": "You don reach your monthly limit. Upgrade make you continue!",
        "yo":  "Ẹ ti dé ààlà oṣù. Ṣe ìgbéga láti tẹ̀síwájú!",
        "ha":  "Kun kai iyakar watan ku. Inganta don ci gaba!",
    },
}


def t(key: str, lang: Optional[str] = None, **kwargs) -> str:
    """
    Look up a translated string.
    Falls back to English if the key or language is missing.
    Supports format kwargs: t("greeting", lang="en", name="Buhari")
    """
    lang = lang or DEFAULT_LANG
    entry = _CATALOG.get(key)
    if not entry:
        return key

    text = entry.get(lang) or entry.get(DEFAULT_LANG, key)

    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass

    return text


def get_user_lang(user: Optional[dict]) -> str:
    """Extract language preference from a user record."""
    if not user:
        return DEFAULT_LANG
    return user.get("language", DEFAULT_LANG)
