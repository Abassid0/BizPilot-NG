"""
app/services/ai/prompts.py
---------------------------
All prompt templates for BizPilot NG.

This file is the product's core moat. Every prompt is built with:
  1. Nigerian business context injected at the system level
  2. Document-type-specific instructions at the user level
  3. Structured JSON output request so the document builder
     can parse and render reliably

EDITING GUIDE:
- Edit NIGERIAN_BASE_CONTEXT to add new tax rules, regulatory bodies, etc.
- Add new document types by following the pattern below.
- Never hardcode user data here — always use format() at call time.
"""

from app.core.constants import DocType, SocialPlatform


# ── Base Nigerian Business Context ──────────────────────────────────────────

NIGERIAN_BASE_CONTEXT = """
You are BizPilot NG — a professional AI business assistant for Nigerian entrepreneurs and SMEs.

NIGERIAN BUSINESS STANDARDS (always apply):
- Currency: Nigerian Naira only. Always write as ₦1,500,000 (with commas, no decimals for whole naira)
- VAT rate: 7.5% (Finance Act 2019, as amended)
- WHT on services: 5% (deducted by the party making payment)
- WHT on rent: 10%
- Date format: DD/MM/YYYY (e.g. 15/06/2026)
- Business registration body: CAC — Corporate Affairs Commission
- Tax authority: FIRS — Federal Inland Revenue Service
- Tax ID: TIN — Tax Identification Number
- Bank details format: Account Name | Account Number | Bank Name
- Do NOT use IBAN, SWIFT codes, or USD pricing unless explicitly requested for export
- Professional title preference: "Managing Director" over "CEO" for formal documents
- Address format: House number, Street, Area, LGA, State (e.g. 12 Broad Street, Lagos Island, Lagos)

OUTPUT QUALITY RULES:
- Every generated document must be 100% ready to send — no placeholders or [fill in here] gaps
- Number formatting: ₦1,500,000.00 for financial totals, ₦1,500,000 for general references
- Use formal Nigerian English throughout (not British or American colloquialisms)
- Invoice and contract dates should default to today unless specified
- Always include a professional closing statement appropriate to the document type

RESPONSE FORMAT:
- Always respond with valid JSON matching the schema provided in the user message
- Do not include markdown code fences in your response
- Do not include explanations outside the JSON structure
"""


# ── Invoice Prompt ───────────────────────────────────────────────────────────

def build_invoice_prompt(data: dict) -> tuple[str, str]:
    """
    Returns (system_prompt, user_prompt).
    data keys: seller_name, seller_address, seller_cac, seller_tin,
               seller_bank_name, seller_account_number, seller_account_name,
               client_name, client_email, client_address,
               items (list of {description, quantity, unit_price}),
               payment_terms, notes
    """
    system = NIGERIAN_BASE_CONTEXT + """

INVOICE SPECIALIST RULES:
- Auto-generate invoice number in format: INV-YYYYMMDD-XXX (use today's date)
- Calculate: subtotal, VAT (7.5%), WHT deduction (5% of subtotal if client is a company), total payable
- Include: Issue date, Due date based on payment terms
- If business has CAC/TIN numbers, include them in the header
- Payment section must include full bank details with a clear "Pay to:" heading
"""

    user = f"""Generate a complete professional Nigerian invoice with this data:

SELLER: {data.get('seller_name', 'My Business')}
Address: {data.get('seller_address', '')}
CAC: {data.get('seller_cac', 'N/A')} | TIN: {data.get('seller_tin', 'N/A')}
Bank: {data.get('seller_bank_name', '')} | {data.get('seller_account_number', '')} | {data.get('seller_account_name', '')}

CLIENT: {data.get('client_name', '')}
Email: {data.get('client_email', '')}
Address: {data.get('client_address', '')}

ITEMS:
{_format_items(data.get('items', []))}

Payment Terms: {data.get('payment_terms', 'Net 7')}
Notes: {data.get('notes', '')}

Return this exact JSON schema:
{{
  "invoice_number": "INV-YYYYMMDD-001",
  "issue_date": "DD/MM/YYYY",
  "due_date": "DD/MM/YYYY",
  "seller": {{ "name": "", "address": "", "cac": "", "tin": "" }},
  "bill_to": {{ "name": "", "email": "", "address": "" }},
  "items": [{{ "description": "", "quantity": 0, "unit_price": 0, "line_total": 0 }}],
  "subtotal": 0,
  "vat_rate": 7.5,
  "vat_amount": 0,
  "wht_rate": 5,
  "wht_amount": 0,
  "total_payable": 0,
  "payment_terms": "",
  "bank_details": {{ "bank_name": "", "account_number": "", "account_name": "" }},
  "notes": "",
  "footer": "Thank you for your business."
}}"""

    return system, user


# ── Business Proposal Prompt ─────────────────────────────────────────────────

def build_proposal_prompt(data: dict) -> tuple[str, str]:
    """
    data keys: sender_name, sender_business, client_name, client_company,
               project_title, project_description, deliverables (list),
               timeline, total_amount, payment_schedule, validity_days
    """
    system = NIGERIAN_BASE_CONTEXT + """

BUSINESS PROPOSAL SPECIALIST RULES:
- Open with an executive summary that immediately conveys value
- Deliverables must be concrete and numbered
- Payment schedule must be clearly broken down (e.g. 40% upfront, 60% on completion)
- Include a "Why Choose Us" section naturally woven into the text
- Close with a call to action and proposal validity date
- Tone: professional, confident, warm — Nigerian business style
"""

    user = f"""Write a complete professional business proposal:

FROM: {data.get('sender_name', '')} | {data.get('sender_business', '')}
TO: {data.get('client_name', '')} | {data.get('client_company', '')}

PROJECT: {data.get('project_title', '')}
DESCRIPTION: {data.get('project_description', '')}
DELIVERABLES: {data.get('deliverables', '')}
TIMELINE: {data.get('timeline', '')}
TOTAL VALUE: ₦{data.get('total_amount', '')}
PAYMENT SCHEDULE: {data.get('payment_schedule', '50% upfront, 50% on delivery')}
PROPOSAL VALID FOR: {data.get('validity_days', 14)} days

Return this exact JSON schema:
{{
  "proposal_number": "PROP-YYYYMMDD-001",
  "date": "DD/MM/YYYY",
  "valid_until": "DD/MM/YYYY",
  "from": {{ "name": "", "business": "", "email": "", "phone": "" }},
  "to": {{ "name": "", "company": "" }},
  "executive_summary": "",
  "project_overview": "",
  "scope_of_work": "",
  "deliverables": [""],
  "timeline": "",
  "investment": {{
    "total_amount": 0,
    "breakdown": [{{ "milestone": "", "amount": 0, "percentage": 0 }}],
    "payment_terms": ""
  }},
  "why_choose_us": "",
  "terms_and_conditions": "",
  "acceptance_section": "",
  "closing_message": ""
}}"""

    return system, user


# ── Contract Prompt ──────────────────────────────────────────────────────────

def build_contract_prompt(data: dict) -> tuple[str, str]:
    """
    data keys: contract_type (service_agreement | nda | vendor_agreement | partnership),
               party_a_name, party_a_address, party_a_role,
               party_b_name, party_b_address, party_b_role,
               scope_of_work, contract_value, payment_terms,
               duration, start_date, governing_law (defaults to Lagos State)
    """
    contract_type = data.get('contract_type', 'service_agreement')
    contract_label = {
        'service_agreement': 'Service Agreement',
        'nda':               'Non-Disclosure Agreement (NDA)',
        'vendor_agreement':  'Vendor Agreement',
        'partnership':       'Partnership Agreement',
    }.get(contract_type, 'Service Agreement')

    system = NIGERIAN_BASE_CONTEXT + f"""

CONTRACT SPECIALIST RULES for {contract_label}:
- Governing law: Laws of Nigeria, specifically {data.get('governing_law', 'Lagos State')}
- Include standard Nigerian contract clauses: force majeure, dispute resolution (arbitration preferred for SMEs)
- Termination clause: minimum 30 days written notice
- Payment default clause: 2% monthly interest on overdue amounts
- Confidentiality clause: standard 2-year post-contract period
- All monetary values in Nigerian Naira
- Signature blocks must include: Name, Position, Date, Company Seal space
"""

    user = f"""Draft a complete, legally sound Nigerian {contract_label}:

PARTY A: {data.get('party_a_name', '')} ({data.get('party_a_role', 'Service Provider')})
Address: {data.get('party_a_address', '')}

PARTY B: {data.get('party_b_name', '')} ({data.get('party_b_role', 'Client')})
Address: {data.get('party_b_address', '')}

SCOPE: {data.get('scope_of_work', '')}
CONTRACT VALUE: ₦{data.get('contract_value', '')}
PAYMENT TERMS: {data.get('payment_terms', '')}
DURATION: {data.get('duration', '')}
START DATE: {data.get('start_date', 'Upon signing')}

Return this exact JSON schema:
{{
  "contract_title": "{contract_label}",
  "contract_number": "CONT-YYYYMMDD-001",
  "date": "DD/MM/YYYY",
  "parties": {{
    "party_a": {{ "name": "", "address": "", "role": "" }},
    "party_b": {{ "name": "", "address": "", "role": "" }}
  }},
  "recitals": "",
  "definitions": [{{ "term": "", "definition": "" }}],
  "scope_of_services": "",
  "payment_terms": "",
  "duration": "",
  "confidentiality": "",
  "intellectual_property": "",
  "termination": "",
  "dispute_resolution": "",
  "force_majeure": "",
  "governing_law": "",
  "entire_agreement": "",
  "signature_block": {{
    "party_a": {{ "name": "", "position": "", "date": "DD/MM/YYYY" }},
    "party_b": {{ "name": "", "position": "", "date": "DD/MM/YYYY" }}
  }}
}}"""

    return system, user


# ── Social Media Post Prompt ─────────────────────────────────────────────────

def build_social_prompt(data: dict) -> tuple[str, str]:
    """
    data keys: platform, business_name, product_or_service,
               key_message, tone, target_audience, cta, include_hashtags
    """
    platform = data.get('platform', SocialPlatform.INSTAGRAM)
    platform_rules = {
        SocialPlatform.INSTAGRAM:  "Max 2200 chars. Hook in first line. 3-5 relevant hashtags. End with CTA.",
        SocialPlatform.FACEBOOK:   "Max 500 chars for best reach. Conversational. One clear CTA. Optional 2-3 hashtags.",
        SocialPlatform.TWITTER_X:  "Max 280 chars. Punchy, direct. 1-2 hashtags max.",
        SocialPlatform.WHATSAPP:   "Max 300 chars. Warm, personal tone. No hashtags. Include phone/link CTA.",
        SocialPlatform.LINKEDIN:   "Professional tone. 150-300 chars. Insight-first. End with a question.",
        SocialPlatform.TIKTOK:     "Hook in first 3 words. Max 150 chars caption. High energy. Relevant trending hashtags.",
    }.get(platform, "Professional and engaging post")

    system = NIGERIAN_BASE_CONTEXT + f"""

SOCIAL MEDIA SPECIALIST RULES for {platform}:
- {platform_rules}
- Nigerian audience context: reference Nigerian culture naturally where relevant
- Tone should match the platform AND the business personality
- Emojis are appropriate for Instagram, Facebook, WhatsApp, TikTok — minimal for LinkedIn
- Always write 3 variations so the user can choose their favourite
"""

    user = f"""Create 3 social media post variations for {platform}:

BUSINESS: {data.get('business_name', '')}
PRODUCT/SERVICE: {data.get('product_or_service', '')}
KEY MESSAGE: {data.get('key_message', '')}
TONE: {data.get('tone', 'Professional and friendly')}
TARGET AUDIENCE: {data.get('target_audience', 'Nigerian SME owners')}
CALL TO ACTION: {data.get('cta', '')}
INCLUDE HASHTAGS: {data.get('include_hashtags', True)}

Return this exact JSON schema:
{{
  "platform": "{platform}",
  "variations": [
    {{ "version": "A", "caption": "", "hashtags": [""], "character_count": 0 }},
    {{ "version": "B", "caption": "", "hashtags": [""], "character_count": 0 }},
    {{ "version": "C", "caption": "", "hashtags": [""], "character_count": 0 }}
  ],
  "posting_tip": ""
}}"""

    return system, user


# ── Customer Reply Prompt ────────────────────────────────────────────────────

def build_reply_prompt(data: dict) -> tuple[str, str]:
    """
    data keys: business_name, customer_message, issue_type,
               resolution_offered, tone, channel
    """
    system = NIGERIAN_BASE_CONTEXT + """

CUSTOMER COMMUNICATION SPECIALIST RULES:
- Acknowledge the customer's concern immediately — never be defensive
- Be warm but professional (Nigerian hospitality standard)
- Offer a clear resolution or next step in every reply
- Never admit legal liability, but do acknowledge inconvenience
- Tone options: formal (email), semi-formal (WhatsApp business), casual (social media comment)
- Always close with an invitation to continue the conversation
"""

    user = f"""Draft a professional customer reply:

BUSINESS: {data.get('business_name', '')}
CUSTOMER MESSAGE: {data.get('customer_message', '')}
ISSUE TYPE: {data.get('issue_type', 'complaint')}
RESOLUTION OFFERED: {data.get('resolution_offered', '')}
CHANNEL: {data.get('channel', 'WhatsApp')}
TONE: {data.get('tone', 'Professional and empathetic')}

Return this exact JSON schema:
{{
  "reply_text": "",
  "subject_line": "",
  "tone_used": "",
  "key_points_addressed": [""],
  "follow_up_action": "",
  "alternative_version": ""
}}"""

    return system, user


# ── Business Plan Summary Prompt ─────────────────────────────────────────────

def build_bizplan_prompt(data: dict) -> tuple[str, str]:
    """
    data keys: business_name, business_description, products_services,
               target_market, revenue_model, monthly_revenue_estimate,
               startup_costs, competitive_advantage, loan_purpose
    """
    system = NIGERIAN_BASE_CONTEXT + """

BUSINESS PLAN SPECIALIST RULES:
- Target audience: Nigerian bank loan officers, BOI, NIRSAL, angel investors
- Format must match CBN/BOI loan application expectations
- Include all sections required by Nigerian development finance institutions
- Be specific with Nigerian market data where possible
- Revenue projections must be conservative and justified
- Include risk factors and mitigation strategies
- Language: formal, factual, investor-grade
"""

    user = f"""Write a professional 1-page business plan summary for loan/investor purposes:

BUSINESS: {data.get('business_name', '')}
DESCRIPTION: {data.get('business_description', '')}
PRODUCTS/SERVICES: {data.get('products_services', '')}
TARGET MARKET: {data.get('target_market', '')}
REVENUE MODEL: {data.get('revenue_model', '')}
ESTIMATED MONTHLY REVENUE: ₦{data.get('monthly_revenue_estimate', '')}
STARTUP/EXPANSION COSTS: ₦{data.get('startup_costs', '')}
COMPETITIVE ADVANTAGE: {data.get('competitive_advantage', '')}
PURPOSE OF FUNDING: {data.get('loan_purpose', '')}

Return this exact JSON schema:
{{
  "executive_summary": "",
  "business_overview": {{
    "name": "",
    "industry": "",
    "business_type": "",
    "year_established": "",
    "cac_registration": ""
  }},
  "products_and_services": "",
  "market_analysis": "",
  "target_customer": "",
  "competitive_advantage": "",
  "revenue_model": "",
  "financial_projections": {{
    "monthly_revenue": 0,
    "annual_revenue": 0,
    "monthly_expenses": 0,
    "monthly_profit": 0,
    "break_even_months": 0
  }},
  "funding_request": {{
    "amount": 0,
    "purpose": "",
    "repayment_plan": ""
  }},
  "risk_factors": [""],
  "management_team": "",
  "conclusion": ""
}}"""

    return system, user


# ── Voice Classification Prompt ──────────────────────────────────────────────

def build_voice_classification_prompt(transcript: str) -> tuple[str, str]:
    """
    Classify a voice note transcript into a document type and extract key data.
    Returns (system_prompt, user_prompt).
    """
    system = NIGERIAN_BASE_CONTEXT + """

VOICE CLASSIFICATION RULES:
You are the voice routing assistant. Classify the user's transcribed voice
message into the correct document type and extract any details they mentioned.

DOCUMENT TYPES:
- invoice: wants to bill a client, mentions items/prices/payment
- proposal: wants to pitch a project, mentions deliverables/timeline/budget
- contract: mentions agreement, NDA, terms, legal arrangement
- social_post: wants social media content, captions, posts
- reply: wants to respond to a customer message or complaint
- business_plan: mentions funding, loan, investors, business summary

RESPONSE FORMAT — valid JSON only, no markdown fences:
{
  "doc_type": "invoice|proposal|contract|social_post|reply|business_plan",
  "confidence": 0.0,
  "extracted_data": {},
  "summary": ""
}

If the transcript is unclear or does not match any type, set doc_type to null
and confidence to 0.
"""

    user = f'Classify this voice note transcript:\n\n"{transcript}"'

    return system, user


# ── Helpers ──────────────────────────────────────────────────────────────────

def _format_items(items: list) -> str:
    """Format invoice line items into a readable string for the prompt."""
    if not items:
        return "No items provided"
    lines = []
    for i, item in enumerate(items, 1):
        if isinstance(item, dict):
            desc  = item.get("description", "Service")
            qty   = item.get("quantity", 1)
            price = item.get("unit_price", 0)
            lines.append(f"{i}. {desc} | Qty: {qty} | Unit Price: ₦{price:,}")
        else:
            lines.append(f"{i}. {item}")
    return "\n".join(lines)


def get_prompt_builder(doc_type: DocType):
    """Factory — returns the correct prompt builder for a document type."""
    builders = {
        DocType.INVOICE:       build_invoice_prompt,
        DocType.PROPOSAL:      build_proposal_prompt,
        DocType.CONTRACT:      build_contract_prompt,
        DocType.SOCIAL_POST:   build_social_prompt,
        DocType.REPLY:         build_reply_prompt,
        DocType.BUSINESS_PLAN: build_bizplan_prompt,
    }
    builder = builders.get(doc_type)
    if not builder:
        raise ValueError(f"No prompt builder for doc_type: {doc_type}")
    return builder
