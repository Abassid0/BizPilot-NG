"""
app/core/constants.py
---------------------
All application-wide constants.
No logic here — pure data definitions.
"""

from enum import Enum


# ── Subscription Tiers ─────────────────────────────────────────────────────

class SubscriptionTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"
    COMMANDER = "commander"  # legacy alias for business


TIER_LABELS = {
    SubscriptionTier.FREE:       "Starter (Free)",
    SubscriptionTier.PRO:        "Pro",
    SubscriptionTier.BUSINESS:   "Business",
    SubscriptionTier.ENTERPRISE: "Enterprise",
    SubscriptionTier.COMMANDER:  "Business",
}

TIER_LIMITS = {
    SubscriptionTier.FREE:       50,
    SubscriptionTier.PRO:        999999,
    SubscriptionTier.BUSINESS:   999999,
    SubscriptionTier.ENTERPRISE: 999999,
    SubscriptionTier.COMMANDER:  999999,
}

TIER_PRICES_KOBO = {
    SubscriptionTier.FREE:       0,
    SubscriptionTier.PRO:        500000,    # ₦5,000
    SubscriptionTier.BUSINESS:   1500000,   # ₦15,000
    SubscriptionTier.ENTERPRISE: 0,         # custom pricing
    SubscriptionTier.COMMANDER:  1500000,
}

TIER_PRICES_NAIRA = {
    SubscriptionTier.FREE:       0,
    SubscriptionTier.PRO:        5000,
    SubscriptionTier.BUSINESS:   15000,
    SubscriptionTier.ENTERPRISE: 0,
    SubscriptionTier.COMMANDER:  15000,
}


# ── Document Types ──────────────────────────────────────────────────────────

class DocType(str, Enum):
    INVOICE       = "invoice"
    PROPOSAL      = "proposal"
    CONTRACT      = "contract"
    SOCIAL_POST   = "social_post"
    REPLY         = "reply"
    BUSINESS_PLAN = "business_plan"


DOC_TYPE_LABELS = {
    DocType.INVOICE:       "📄 Invoice",
    DocType.PROPOSAL:      "📋 Business Proposal",
    DocType.CONTRACT:      "📝 Contract / NDA",
    DocType.SOCIAL_POST:   "📱 Social Media Content",
    DocType.REPLY:         "💬 Customer Reply",
    DocType.BUSINESS_PLAN: "📊 Business Plan Summary",
}

DOC_TYPE_COMMANDS = {
    "/invoice":   DocType.INVOICE,
    "/proposal":  DocType.PROPOSAL,
    "/contract":  DocType.CONTRACT,
    "/post":      DocType.SOCIAL_POST,
    "/reply":     DocType.REPLY,
    "/bizplan":   DocType.BUSINESS_PLAN,
}


# ── Business Types ──────────────────────────────────────────────────────────

NIGERIAN_BUSINESS_TYPES = [
    "Trading / Retail",
    "Food & Catering",
    "Fashion & Clothing",
    "Logistics & Delivery",
    "Events & Entertainment",
    "Tech & Digital Services",
    "Agriculture & Farming",
    "Construction & Real Estate",
    "Education & Training",
    "Health & Wellness",
    "Beauty & Personal Care",
    "Manufacturing",
    "Consulting & Professional Services",
    "Other",
]

NIGERIAN_INDUSTRIES = [
    "FMCG",
    "Fintech",
    "Agribusiness",
    "Oil & Gas",
    "Construction",
    "Healthcare",
    "Education",
    "Retail",
    "Hospitality",
    "Transportation",
    "Fashion",
    "Media & Entertainment",
    "ICT",
    "Other",
]


# ── Social Media Platforms ──────────────────────────────────────────────────

class SocialPlatform(str, Enum):
    INSTAGRAM   = "instagram"
    FACEBOOK    = "facebook"
    TWITTER_X   = "twitter_x"
    WHATSAPP    = "whatsapp"
    LINKEDIN    = "linkedin"
    TIKTOK      = "tiktok"

SOCIAL_PLATFORM_LABELS = {
    SocialPlatform.INSTAGRAM:  "Instagram",
    SocialPlatform.FACEBOOK:   "Facebook",
    SocialPlatform.TWITTER_X:  "X (Twitter)",
    SocialPlatform.WHATSAPP:   "WhatsApp Broadcast",
    SocialPlatform.LINKEDIN:   "LinkedIn",
    SocialPlatform.TIKTOK:     "TikTok",
}


# ── Nigerian Tax & Compliance ───────────────────────────────────────────────

NIGERIAN_VAT_RATE          = 0.075     # 7.5% — Finance Act 2019
NIGERIAN_WHT_SERVICE_RATE  = 0.05      # 5% on service contracts
NIGERIAN_WHT_DIVIDEND_RATE = 0.10      # 10% on dividends
NIGERIAN_WHT_RENT_RATE     = 0.10      # 10% on rent


# ── Conversation States (for python-telegram-bot ConversationHandler) ───────

# Onboarding
ONBOARD_NAME        = 0
ONBOARD_BIZ_NAME    = 1
ONBOARD_BIZ_TYPE    = 2

# Invoice
INV_CLIENT_NAME     = 10
INV_CLIENT_EMAIL    = 11
INV_ITEMS           = 12
INV_PAYMENT_TERMS   = 13
INV_BANK_DETAILS    = 14
INV_CONFIRM         = 15

# Proposal
PROP_CLIENT_NAME    = 20
PROP_PROJECT_DESC   = 21
PROP_DELIVERABLES   = 22
PROP_AMOUNT         = 23
PROP_TIMELINE       = 24
PROP_CONFIRM        = 25

# Contract
CONT_TYPE           = 30
CONT_PARTY_A        = 31
CONT_PARTY_B        = 32
CONT_SCOPE          = 33
CONT_VALUE          = 34
CONT_DURATION       = 35
CONT_CONFIRM        = 36

# Social Post
SOC_PLATFORM        = 40
SOC_PRODUCT         = 41
SOC_TONE            = 42
SOC_CTA             = 43
SOC_CONFIRM         = 44

# Customer Reply
REPLY_CONTEXT       = 50
REPLY_ISSUE         = 51
REPLY_TONE          = 52
REPLY_CONFIRM       = 53

# Business Plan
BIZPLAN_DESC        = 60
BIZPLAN_MARKET      = 61
BIZPLAN_REVENUE     = 62
BIZPLAN_PURPOSE     = 63
BIZPLAN_CONFIRM     = 64

# Profile Update
PROFILE_FIELD       = 70
PROFILE_VALUE       = 71

# Expense Tracking
EXP_AMOUNT          = 80
EXP_DESCRIPTION     = 81
EXP_CATEGORY        = 82
EXP_VENDOR          = 83
EXP_DATE            = 84
EXP_CONFIRM         = 85

# Financial Dashboard
DASH_QUERY          = 90

# Team Management
TEAM_CREATE_NAME    = 100
TEAM_INVITE_ROLE    = 101

# Language Selection
LANG_SELECT         = 110


# ── Expense Categories ─────────────────────────────────────────────────────

EXPENSE_CATEGORIES = [
    "Transport & Logistics",
    "Food & Catering",
    "Office Supplies",
    "Rent & Utilities",
    "Staff & Salaries",
    "Marketing & Ads",
    "Professional Services",
    "Inventory & Stock",
    "Equipment & Tools",
    "Communication & Internet",
    "Insurance",
    "Bank Charges & Fees",
    "Taxes & Government",
    "Miscellaneous",
]


# ── Output Formats ──────────────────────────────────────────────────────────

class OutputFormat(str, Enum):
    PDF       = "pdf"
    DOCX      = "docx"
    TEXT      = "text"       # Free tier in-chat preview


# ── Bot Messages ────────────────────────────────────────────────────────────

WELCOME_MESSAGE = """
👋 Welcome to *BizPilot NG* — Your AI Business Assistant!

I help Nigerian entrepreneurs create professional:
📄 Invoices
📋 Business Proposals  
📝 Contracts & NDAs
📱 Social Media Content
💬 Customer Replies
📊 Business Plan Summaries

All documents are Nigeria-ready — correct VAT, Naira formatting, CAC/FIRS compliance.

Let's set up your business profile first. What's your name?
"""

HELP_MESSAGE = """
*BizPilot NG — Available Commands*

*Documents*
📄 /invoice — Generate a professional invoice
📋 /proposal — Write a business proposal
📝 /contract — Create a contract or NDA
📱 /post — Generate social media content
💬 /reply — Draft a customer reply
📊 /bizplan — Write a business plan summary

*Finance*
💰 /expense — Log an expense
📸 /scan — Scan a receipt (send a photo)
📈 /dashboard — Financial summary & reports
🧾 /tax — Tax compliance & calculations
🔍 /insights — AI business health reports

*Account*
⚙️ /profile — Update your business details
💳 /upgrade — View subscription plans
📂 /history — Your recent documents
👥 /team — Manage your team
🌍 /language — Change language
❓ /help — Show this menu
🚫 /cancel — Cancel current operation

💡 *Tips:* Send a photo of a receipt to auto-scan it, or send a voice note!
"""

UPGRADE_MESSAGE = """
💳 *BizPilot NG Subscription Plans*

*🆓 Starter (Free)*
• 50 transactions per month
• Basic expense tracking
• All document types
• Text preview in chat

*⚡ Pro — ₦5,000/month*
• Unlimited transactions
• PDF & DOCX downloads
• Tax compliance & insights
• AI business reports
• Receipt OCR scanning

*🏢 Business — ₦15,000/month*
• Everything in Pro
• Multi-user team seats
• Accountant access
• API access
• Priority support

*🏦 Enterprise — Custom*
• White-label for accounting firms
• Custom integrations
• Dedicated support
• Contact us for pricing

Tap below to upgrade 👇
"""
