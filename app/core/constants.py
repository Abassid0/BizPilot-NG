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
    COMMANDER = "commander"


TIER_LABELS = {
    SubscriptionTier.FREE:       "Starter (Free)",
    SubscriptionTier.PRO:        "Pro Operator",
    SubscriptionTier.COMMANDER:  "Business Commander",
}

TIER_LIMITS = {
    SubscriptionTier.FREE:       5,
    SubscriptionTier.PRO:        999999,
    SubscriptionTier.COMMANDER:  999999,
}

TIER_PRICES_KOBO = {
    SubscriptionTier.FREE:       0,
    SubscriptionTier.PRO:        499900,   # ₦4,999
    SubscriptionTier.COMMANDER:  1299900,  # ₦12,999
}

TIER_PRICES_NAIRA = {
    SubscriptionTier.FREE:       0,
    SubscriptionTier.PRO:        4999,
    SubscriptionTier.COMMANDER:  12999,
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
    "/plan":      DocType.BUSINESS_PLAN,
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
ONBOARD_INDUSTRY    = 3

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

📄 /invoice — Generate a professional invoice
📋 /proposal — Write a business proposal
📝 /contract — Create a contract or NDA
📱 /post — Generate social media content
💬 /reply — Draft a customer reply
📊 /bizplan — Write a business plan summary

⚙️ /profile — Update your business details
💳 /upgrade — View subscription plans
📂 /history — Your recent documents
❓ /help — Show this menu
🚫 /cancel — Cancel current operation

💡 *Pro tip:* Send a voice note and I'll understand it too!
"""

UPGRADE_MESSAGE = """
💳 *BizPilot NG Subscription Plans*

*🆓 Starter (Free)*
• 5 documents per month
• Text preview in chat
• All document types

*⚡ Pro Operator — ₦4,999/month*
• Unlimited documents
• PDF & DOCX downloads
• Professional formatting
• No watermarks
• Priority processing

*🏆 Business Commander — ₦12,999/month*
• Everything in Pro
• Your business logo on documents
• 3 team member seats
• Dedicated support

Tap below to upgrade 👇
"""
