"""
tests/test_phase3.py
-----------------------
Tests for Phase 3 features:
  - Pricing restructure (BP-20)
  - i18n translations (BP-22)
  - Insights prompt builder (BP-17)
  - WhatsApp config (BP-18)
  - Team constants (BP-19)

Run with:
    pytest tests/test_phase3.py -v
"""

import pytest
from app.core.constants import (
    SubscriptionTier,
    TIER_LABELS,
    TIER_LIMITS,
    TIER_PRICES_KOBO,
    TIER_PRICES_NAIRA,
    EXPENSE_CATEGORIES,
    TEAM_CREATE_NAME,
    TEAM_INVITE_ROLE,
    LANG_SELECT,
)


# ════════════════════════════════════════════════════════════════
# PRICING RESTRUCTURE (BP-20)
# ════════════════════════════════════════════════════════════════

class TestPricingRestructure:

    def test_business_tier_exists(self):
        assert SubscriptionTier.BUSINESS == "business"

    def test_enterprise_tier_exists(self):
        assert SubscriptionTier.ENTERPRISE == "enterprise"

    def test_commander_is_legacy_alias(self):
        assert SubscriptionTier.COMMANDER == "commander"
        assert TIER_LABELS[SubscriptionTier.COMMANDER] == "Business"

    def test_free_tier_limit_is_fifty(self):
        assert TIER_LIMITS[SubscriptionTier.FREE] == 50

    def test_pro_price_is_five_thousand(self):
        assert TIER_PRICES_NAIRA[SubscriptionTier.PRO] == 5000

    def test_business_price_is_fifteen_thousand(self):
        assert TIER_PRICES_NAIRA[SubscriptionTier.BUSINESS] == 15000

    def test_pro_kobo_is_500000(self):
        assert TIER_PRICES_KOBO[SubscriptionTier.PRO] == 500000

    def test_business_kobo_is_1500000(self):
        assert TIER_PRICES_KOBO[SubscriptionTier.BUSINESS] == 1500000

    def test_enterprise_price_is_custom(self):
        assert TIER_PRICES_NAIRA[SubscriptionTier.ENTERPRISE] == 0

    def test_all_tiers_have_labels(self):
        for tier in SubscriptionTier:
            assert tier in TIER_LABELS, f"{tier} missing label"

    def test_all_tiers_have_limits(self):
        for tier in SubscriptionTier:
            assert tier in TIER_LIMITS, f"{tier} missing limit"

    def test_all_tiers_have_prices(self):
        for tier in SubscriptionTier:
            assert tier in TIER_PRICES_NAIRA, f"{tier} missing Naira price"
            assert tier in TIER_PRICES_KOBO, f"{tier} missing kobo price"


# ════════════════════════════════════════════════════════════════
# i18n TRANSLATIONS (BP-22)
# ════════════════════════════════════════════════════════════════

class TestI18n:

    def test_import_i18n(self):
        from app.core.i18n import t, SUPPORTED_LANGUAGES, DEFAULT_LANG
        assert DEFAULT_LANG == "en"

    def test_supported_languages(self):
        from app.core.i18n import SUPPORTED_LANGUAGES
        assert "en" in SUPPORTED_LANGUAGES
        assert "pcm" in SUPPORTED_LANGUAGES
        assert "yo" in SUPPORTED_LANGUAGES
        assert "ha" in SUPPORTED_LANGUAGES

    def test_english_translation(self):
        from app.core.i18n import t
        text = t("welcome", lang="en")
        assert "BizPilot NG" in text

    def test_pidgin_translation(self):
        from app.core.i18n import t
        text = t("welcome", lang="pcm")
        assert "dey" in text.lower()

    def test_yoruba_translation(self):
        from app.core.i18n import t
        text = t("welcome", lang="yo")
        assert len(text) > 20

    def test_hausa_translation(self):
        from app.core.i18n import t
        text = t("welcome", lang="ha")
        assert "Barka" in text

    def test_fallback_to_english(self):
        from app.core.i18n import t
        text = t("welcome", lang="xx_unknown")
        assert "BizPilot NG" in text

    def test_missing_key_returns_key(self):
        from app.core.i18n import t
        result = t("nonexistent_key_xyz")
        assert result == "nonexistent_key_xyz"

    def test_all_keys_have_all_languages(self):
        from app.core.i18n import _CATALOG, SUPPORTED_LANGUAGES
        for key, translations in _CATALOG.items():
            for lang in SUPPORTED_LANGUAGES:
                assert lang in translations, f"Key '{key}' missing translation for '{lang}'"

    def test_get_user_lang_default(self):
        from app.core.i18n import get_user_lang
        assert get_user_lang(None) == "en"
        assert get_user_lang({}) == "en"

    def test_get_user_lang_from_user(self):
        from app.core.i18n import get_user_lang
        assert get_user_lang({"language": "pcm"}) == "pcm"

    def test_expense_logged_all_langs(self):
        from app.core.i18n import t
        for lang in ["en", "pcm", "yo", "ha"]:
            text = t("expense_logged", lang=lang)
            assert len(text) > 5

    def test_language_changed_all_langs(self):
        from app.core.i18n import t
        for lang in ["en", "pcm", "yo", "ha"]:
            text = t("language_changed", lang=lang)
            assert len(text) > 5


# ════════════════════════════════════════════════════════════════
# INSIGHTS PROMPT (BP-17)
# ════════════════════════════════════════════════════════════════

class TestInsightsPrompt:

    def test_insights_prompt_builder_exists(self):
        from app.services.ai.prompts import build_insights_prompt
        assert callable(build_insights_prompt)

    def test_insights_prompt_returns_tuple(self):
        from app.services.ai.prompts import build_insights_prompt
        system, user = build_insights_prompt({"current_month": {}}, "monthly")
        assert isinstance(system, str)
        assert isinstance(user, str)

    def test_insights_prompt_contains_health_score(self):
        from app.services.ai.prompts import build_insights_prompt
        system, user = build_insights_prompt({}, "monthly")
        assert "health_score" in system

    def test_insights_prompt_contains_nigerian_context(self):
        from app.services.ai.prompts import build_insights_prompt
        system, _ = build_insights_prompt({}, "monthly")
        assert "Nigerian" in system

    def test_insights_claude_client_method_exists(self):
        from app.services.ai.claude_client import generate_business_insights
        assert callable(generate_business_insights)


# ════════════════════════════════════════════════════════════════
# WHATSAPP SCAFFOLD (BP-18)
# ════════════════════════════════════════════════════════════════

class TestWhatsAppScaffold:

    def test_whatsapp_config_fields_exist(self):
        from app.core.config import Settings
        fields = Settings.model_fields
        assert "whatsapp_access_token" in fields
        assert "whatsapp_phone_number_id" in fields
        assert "whatsapp_verify_token" in fields

    def test_whatsapp_client_module_exists(self):
        from app.services.whatsapp.client import (
            send_text_message,
            send_interactive_buttons,
            send_template_message,
            mark_message_read,
        )
        assert callable(send_text_message)
        assert callable(send_interactive_buttons)

    def test_whatsapp_router_exists(self):
        from app.api.routes.whatsapp import router
        routes = [r.path for r in router.routes]
        assert "/webhook/whatsapp" in routes


# ════════════════════════════════════════════════════════════════
# TEAM MANAGEMENT (BP-19)
# ════════════════════════════════════════════════════════════════

class TestTeamManagement:

    def test_team_conversation_states_exist(self):
        assert isinstance(TEAM_CREATE_NAME, int)
        assert isinstance(TEAM_INVITE_ROLE, int)
        assert TEAM_CREATE_NAME != TEAM_INVITE_ROLE

    def test_team_handler_importable(self):
        from app.bot.handlers.team import build_team_handler
        assert callable(build_team_handler)

    def test_team_db_operations_importable(self):
        from app.db.client import (
            create_team,
            get_user_team,
            get_team_members,
            create_team_invitation,
            accept_team_invitation,
            remove_team_member,
        )
        assert callable(create_team)
        assert callable(get_user_team)
        assert callable(get_team_members)
        assert callable(create_team_invitation)


# ════════════════════════════════════════════════════════════════
# EXPENSE CATEGORIES SANITY
# ════════════════════════════════════════════════════════════════

class TestExpenseCategories:

    def test_fourteen_categories(self):
        assert len(EXPENSE_CATEGORIES) == 14

    def test_transport_category_exists(self):
        assert "Transport & Logistics" in EXPENSE_CATEGORIES

    def test_miscellaneous_is_last(self):
        assert EXPENSE_CATEGORIES[-1] == "Miscellaneous"

    def test_no_duplicates(self):
        assert len(EXPENSE_CATEGORIES) == len(set(EXPENSE_CATEGORIES))


# ════════════════════════════════════════════════════════════════
# PAYSTACK PLAN CODE MAPPING
# ════════════════════════════════════════════════════════════════

class TestPaystackPlanCodes:

    def test_get_plan_code_pro(self):
        from app.services.payments.paystack import get_plan_code
        code = get_plan_code(SubscriptionTier.PRO)
        assert code is not None or code == ""

    def test_get_plan_code_business(self):
        from app.services.payments.paystack import get_plan_code
        code = get_plan_code(SubscriptionTier.BUSINESS)
        assert code is not None or code == ""

    def test_get_plan_code_commander_maps_to_business(self):
        from app.services.payments.paystack import get_plan_code
        biz_code = get_plan_code(SubscriptionTier.BUSINESS)
        cmd_code = get_plan_code(SubscriptionTier.COMMANDER)
        assert biz_code == cmd_code
