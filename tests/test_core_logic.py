"""
tests/test_core_logic.py
--------------------------
Unit tests for pure logic functions that require no external services.

Tests cover:
  - Invoice item parser (_parse_items)
  - Document plain-text formatters
  - Paystack kobo/naira conversion utilities
  - Nigerian VAT/WHT calculations
  - Prompt builder factory (returns correct function)

Run with:
    pytest tests/test_core_logic.py -v
"""

import pytest
from app.bot.handlers.invoice import _parse_items
from app.services.documents.generator import DocumentGenerator
from app.services.payments.paystack import kobo_to_naira, naira_to_kobo, format_naira
from app.core.constants import DocType, SubscriptionTier
from app.services.ai.prompts import get_prompt_builder


# ════════════════════════════════════════════════════════════════
# INVOICE ITEM PARSER
# ════════════════════════════════════════════════════════════════

class TestParseItems:

    def test_single_item_three_parts(self):
        raw = "Web Design Service | 1 | 250000"
        result = _parse_items(raw)
        assert len(result) == 1
        assert result[0]["description"] == "Web Design Service"
        assert result[0]["quantity"]    == 1.0
        assert result[0]["unit_price"]  == 250000.0
        assert result[0]["line_total"]  == 250000.0

    def test_multiple_items(self):
        raw = "Logo Design | 2 | 75000\nCatering Service | 1 | 350000"
        result = _parse_items(raw)
        assert len(result) == 2
        assert result[0]["description"] == "Logo Design"
        assert result[0]["line_total"]  == 150000.0
        assert result[1]["unit_price"]  == 350000.0

    def test_quantity_multiplied_correctly(self):
        raw = "Consultation | 3 | 50000"
        result = _parse_items(raw)
        assert result[0]["line_total"] == 150000.0

    def test_naira_symbol_stripped(self):
        raw = "Printing | 1 | ₦45,000"
        result = _parse_items(raw)
        assert result[0]["unit_price"] == 45000.0

    def test_commas_in_price_stripped(self):
        raw = "Website | 1 | 1,200,000"
        result = _parse_items(raw)
        assert result[0]["unit_price"] == 1200000.0

    def test_two_part_item_defaults_qty_one(self):
        raw = "Flat Rate Service | 80000"
        result = _parse_items(raw)
        assert len(result) == 1
        assert result[0]["quantity"]   == 1
        assert result[0]["unit_price"] == 80000.0

    def test_invalid_line_skipped(self):
        raw = "Invalid line no numbers\nReal Item | 1 | 10000"
        result = _parse_items(raw)
        assert len(result) == 1
        assert result[0]["description"] == "Real Item"

    def test_empty_string_returns_empty_list(self):
        result = _parse_items("")
        assert result == []

    def test_whitespace_stripped_from_description(self):
        raw = "  Event Photography  |  1  |  200000  "
        result = _parse_items(raw)
        assert result[0]["description"] == "Event Photography"


# ════════════════════════════════════════════════════════════════
# PAYSTACK UTILITIES
# ════════════════════════════════════════════════════════════════

class TestPaystackUtils:

    def test_kobo_to_naira_basic(self):
        assert kobo_to_naira(499900) == 4999.0

    def test_kobo_to_naira_zero(self):
        assert kobo_to_naira(0) == 0.0

    def test_kobo_to_naira_commander(self):
        assert kobo_to_naira(1299900) == 12999.0

    def test_naira_to_kobo_basic(self):
        assert naira_to_kobo(4999.0) == 499900

    def test_naira_to_kobo_integer_input(self):
        assert naira_to_kobo(12999) == 1299900

    def test_format_naira_basic(self):
        assert format_naira(4999.0) == "₦4,999.00"

    def test_format_naira_millions(self):
        assert format_naira(1500000.0) == "₦1,500,000.00"

    def test_format_naira_zero(self):
        assert format_naira(0) == "₦0.00"

    def test_roundtrip_naira_kobo(self):
        """Naira → kobo → naira should be lossless for whole numbers."""
        original = 4999.0
        assert kobo_to_naira(naira_to_kobo(original)) == original


# ════════════════════════════════════════════════════════════════
# NIGERIAN VAT / WHT CALCULATIONS
# ════════════════════════════════════════════════════════════════

class TestNigerianTax:
    """Validate that our tax constants and calculations are correct."""

    VAT_RATE = 0.075
    WHT_RATE = 0.05

    def test_vat_on_one_million(self):
        subtotal = 1_000_000
        vat = subtotal * self.VAT_RATE
        assert vat == 75_000.0

    def test_wht_on_service(self):
        subtotal = 500_000
        wht = subtotal * self.WHT_RATE
        assert wht == 25_000.0

    def test_total_after_vat_and_wht(self):
        """
        Nigerian invoicing logic:
          Total payable = subtotal + VAT - WHT
          (WHT is deducted BY the client and remitted to FIRS)
        """
        subtotal = 1_000_000
        vat      = subtotal * self.VAT_RATE
        wht      = subtotal * self.WHT_RATE
        total    = subtotal + vat - wht
        assert total == 1_025_000.0

    def test_vat_rate_is_seven_point_five_percent(self):
        """Confirm we have not accidentally used 5% or 10%."""
        from app.core.constants import NIGERIAN_VAT_RATE
        assert NIGERIAN_VAT_RATE == 0.075

    def test_wht_service_rate_is_five_percent(self):
        from app.core.constants import NIGERIAN_WHT_SERVICE_RATE
        assert NIGERIAN_WHT_SERVICE_RATE == 0.05


# ════════════════════════════════════════════════════════════════
# PROMPT BUILDER FACTORY
# ════════════════════════════════════════════════════════════════

class TestPromptBuilderFactory:

    def test_returns_callable_for_invoice(self):
        builder = get_prompt_builder(DocType.INVOICE)
        assert callable(builder)

    def test_returns_callable_for_proposal(self):
        builder = get_prompt_builder(DocType.PROPOSAL)
        assert callable(builder)

    def test_returns_callable_for_contract(self):
        builder = get_prompt_builder(DocType.CONTRACT)
        assert callable(builder)

    def test_returns_callable_for_social_post(self):
        builder = get_prompt_builder(DocType.SOCIAL_POST)
        assert callable(builder)

    def test_returns_callable_for_reply(self):
        builder = get_prompt_builder(DocType.REPLY)
        assert callable(builder)

    def test_returns_callable_for_business_plan(self):
        builder = get_prompt_builder(DocType.BUSINESS_PLAN)
        assert callable(builder)

    def test_raises_for_unknown_doc_type(self):
        with pytest.raises(ValueError):
            get_prompt_builder("invalid_type")

    def test_invoice_prompt_returns_tuple(self):
        builder = get_prompt_builder(DocType.INVOICE)
        system, user = builder({"client_name": "Test Client", "items": []})
        assert isinstance(system, str)
        assert isinstance(user, str)

    def test_invoice_prompt_contains_nigerian_vat(self):
        builder = get_prompt_builder(DocType.INVOICE)
        system, user = builder({"client_name": "Test Client", "items": []})
        assert "7.5%" in system

    def test_proposal_prompt_contains_naira_symbol(self):
        builder = get_prompt_builder(DocType.PROPOSAL)
        system, user = builder({"client_name": "Dangote Ltd", "total_amount": 500000})
        assert "₦" in user

    def test_system_prompt_contains_firs(self):
        """Every system prompt must reference Nigerian tax authority."""
        for doc_type in DocType:
            builder = get_prompt_builder(doc_type)
            system, _ = builder({})
            assert "FIRS" in system or "Nigerian" in system, \
                f"System prompt for {doc_type} missing Nigerian context"


# ════════════════════════════════════════════════════════════════
# DOCUMENT PLAIN TEXT FORMATTERS
# ════════════════════════════════════════════════════════════════

class TestDocumentFormatters:
    """
    Test the plain-text formatters in DocumentGenerator.
    These run without any external API calls.
    """

    INVOICE_DATA = {
        "invoice_number": "INV-20260611-001",
        "issue_date":     "11/06/2026",
        "due_date":       "18/06/2026",
        "seller":  {"name": "Adewale Ventures", "address": "Lagos", "cac": "RC123456", "tin": "1234567890"},
        "bill_to": {"name": "MTN Nigeria",      "email":   "accounts@mtn.ng", "address": "Falomo, Lagos"},
        "items": [
            {"description": "IT Consulting", "quantity": 5, "unit_price": 50000, "line_total": 250000},
        ],
        "subtotal":      250000,
        "vat_rate":      7.5,
        "vat_amount":    18750,
        "wht_rate":      5,
        "wht_amount":    12500,
        "total_payable": 256250,
        "payment_terms": "Net 7",
        "bank_details":  {"bank_name": "GTBank", "account_number": "0123456789", "account_name": "Adewale Ventures"},
        "notes":         "Thank you.",
        "footer":        "Payment within 7 days appreciated.",
    }

    def test_invoice_text_contains_invoice_number(self):
        text = DocumentGenerator._invoice_to_text(self.INVOICE_DATA)
        assert "INV-20260611-001" in text

    def test_invoice_text_contains_client_name(self):
        text = DocumentGenerator._invoice_to_text(self.INVOICE_DATA)
        assert "MTN Nigeria" in text

    def test_invoice_text_contains_total(self):
        text = DocumentGenerator._invoice_to_text(self.INVOICE_DATA)
        assert "256,250" in text

    def test_invoice_text_contains_bank_details(self):
        text = DocumentGenerator._invoice_to_text(self.INVOICE_DATA)
        assert "GTBank" in text
        assert "0123456789" in text

    def test_invoice_text_contains_vat_line(self):
        text = DocumentGenerator._invoice_to_text(self.INVOICE_DATA)
        assert "VAT" in text

    def test_invoice_text_is_string(self):
        text = DocumentGenerator._invoice_to_text(self.INVOICE_DATA)
        assert isinstance(text, str)
        assert len(text) > 100

    def test_social_text_contains_all_versions(self):
        data = {
            "platform": "instagram",
            "variations": [
                {"version": "A", "caption": "Caption A text", "hashtags": ["#nigerian"], "character_count": 50},
                {"version": "B", "caption": "Caption B text", "hashtags": ["#business"], "character_count": 48},
                {"version": "C", "caption": "Caption C text", "hashtags": ["#sme"],      "character_count": 45},
            ],
            "posting_tip": "Post between 6pm and 9pm for best reach.",
        }
        text = DocumentGenerator._social_to_text(data)
        assert "Version A" in text
        assert "Version B" in text
        assert "Version C" in text
        assert "posting_tip" not in text   # human-readable label, not the key
        assert "Post between" in text

    def test_reply_text_contains_reply(self):
        data = {
            "reply_text":          "Dear valued customer, we sincerely apologise...",
            "subject_line":        "Re: Your Complaint",
            "tone_used":           "empathetic",
            "key_points_addressed": ["delay", "refund"],
            "follow_up_action":    "Send replacement within 48 hours",
            "alternative_version": "Hi, thanks for reaching out...",
        }
        text = DocumentGenerator._reply_to_text(data)
        assert "sincerely apologise" in text
        assert "Re: Your Complaint" in text
        assert "replacement within 48 hours" in text

    def test_bizplan_text_contains_financial_data(self):
        data = {
            "executive_summary":  "A leading logistics company in Lagos.",
            "business_overview":  {"name": "FastMove Ltd", "industry": "Logistics", "cac_registration": "RC123", },
            "market_analysis":    "Lagos has 20M+ residents needing delivery.",
            "competitive_advantage": "Same-day delivery guarantee.",
            "revenue_model":      "Per-delivery fee plus monthly subscription.",
            "financial_projections": {
                "monthly_revenue":  800000,
                "annual_revenue":   9600000,
                "monthly_expenses": 400000,
                "monthly_profit":   400000,
                "break_even_months": 3,
            },
            "funding_request": {
                "amount":          5000000,
                "purpose":         "Fleet expansion",
                "repayment_plan":  "24-month term loan at 12% p.a.",
            },
            "conclusion": "FastMove is positioned to capture 5% market share.",
        }
        text = DocumentGenerator._bizplan_to_text(data)
        assert "800,000" in text
        assert "9,600,000" in text
        assert "Fleet expansion" in text
        assert "FastMove Ltd" in text


# ════════════════════════════════════════════════════════════════
# CONSTANTS SANITY CHECKS
# ════════════════════════════════════════════════════════════════

class TestConstants:

    def test_all_doc_types_have_labels(self):
        from app.core.constants import DOC_TYPE_LABELS
        for doc_type in DocType:
            assert doc_type in DOC_TYPE_LABELS, f"{doc_type} missing from DOC_TYPE_LABELS"

    def test_all_subscription_tiers_have_limits(self):
        from app.core.constants import TIER_LIMITS
        for tier in SubscriptionTier:
            assert tier in TIER_LIMITS, f"{tier} missing from TIER_LIMITS"

    def test_free_tier_limit_is_fifty(self):
        from app.core.constants import TIER_LIMITS
        assert TIER_LIMITS[SubscriptionTier.FREE] == 50

    def test_pro_tier_limit_is_effectively_unlimited(self):
        from app.core.constants import TIER_LIMITS
        assert TIER_LIMITS[SubscriptionTier.PRO] >= 999999

    def test_nigerian_business_types_not_empty(self):
        from app.core.constants import NIGERIAN_BUSINESS_TYPES
        assert len(NIGERIAN_BUSINESS_TYPES) > 5

    def test_conversation_states_are_unique_integers(self):
        """No two states should share the same integer — causes routing bugs."""
        from app.core.constants import (
            ONBOARD_NAME, ONBOARD_BIZ_NAME, ONBOARD_BIZ_TYPE,
            INV_CLIENT_NAME, INV_CLIENT_EMAIL, INV_ITEMS,
            INV_PAYMENT_TERMS, INV_BANK_DETAILS, INV_CONFIRM,
            PROP_CLIENT_NAME, PROP_PROJECT_DESC, PROP_DELIVERABLES,
            PROP_AMOUNT, PROP_TIMELINE, PROP_CONFIRM,
            CONT_TYPE, CONT_PARTY_A, CONT_PARTY_B,
            CONT_SCOPE, CONT_VALUE, CONT_DURATION, CONT_CONFIRM,
            SOC_PLATFORM, SOC_PRODUCT, SOC_TONE, SOC_CTA, SOC_CONFIRM,
            REPLY_CONTEXT, REPLY_ISSUE, REPLY_TONE, REPLY_CONFIRM,
            BIZPLAN_DESC, BIZPLAN_MARKET, BIZPLAN_REVENUE,
            BIZPLAN_PURPOSE, BIZPLAN_CONFIRM,
            EXP_AMOUNT, EXP_DESCRIPTION, EXP_CATEGORY,
            EXP_VENDOR, EXP_DATE, EXP_CONFIRM,
            DASH_QUERY,
            TEAM_CREATE_NAME, TEAM_INVITE_ROLE,
            LANG_SELECT,
        )
        all_states = [
            ONBOARD_NAME, ONBOARD_BIZ_NAME, ONBOARD_BIZ_TYPE,
            INV_CLIENT_NAME, INV_CLIENT_EMAIL, INV_ITEMS,
            INV_PAYMENT_TERMS, INV_BANK_DETAILS, INV_CONFIRM,
            PROP_CLIENT_NAME, PROP_PROJECT_DESC, PROP_DELIVERABLES,
            PROP_AMOUNT, PROP_TIMELINE, PROP_CONFIRM,
            CONT_TYPE, CONT_PARTY_A, CONT_PARTY_B,
            CONT_SCOPE, CONT_VALUE, CONT_DURATION, CONT_CONFIRM,
            SOC_PLATFORM, SOC_PRODUCT, SOC_TONE, SOC_CTA, SOC_CONFIRM,
            REPLY_CONTEXT, REPLY_ISSUE, REPLY_TONE, REPLY_CONFIRM,
            BIZPLAN_DESC, BIZPLAN_MARKET, BIZPLAN_REVENUE,
            BIZPLAN_PURPOSE, BIZPLAN_CONFIRM,
            EXP_AMOUNT, EXP_DESCRIPTION, EXP_CATEGORY,
            EXP_VENDOR, EXP_DATE, EXP_CONFIRM,
            DASH_QUERY,
            TEAM_CREATE_NAME, TEAM_INVITE_ROLE,
            LANG_SELECT,
        ]
        assert len(all_states) == len(set(all_states)), \
            "Duplicate conversation state integer found — will cause routing bugs!"
