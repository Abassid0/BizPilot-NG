# BizPilot Pro

**AI-powered business operations platform for African SMBs.**

Track expenses, generate documents, monitor tax compliance, get AI business insights, and manage your team — all from Telegram or WhatsApp. Built for Nigerian entrepreneurs with Naira formatting, FIRS tax rules (VAT 7.5%, WHT, CIT), and local payment processing via Paystack.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Tech Stack](#tech-stack)
3. [Features](#features)
4. [Project Structure](#project-structure)
5. [Prerequisites](#prerequisites)
6. [Local Development Setup](#local-development-setup)
7. [Environment Variables](#environment-variables)
8. [Database Setup (Supabase)](#database-setup-supabase)
9. [Paystack Setup](#paystack-setup)
10. [Running Locally](#running-locally)
11. [Production Deployment (Railway)](#production-deployment-railway)
12. [Web Dashboard](#web-dashboard)
13. [Bot Commands](#bot-commands)
14. [Document Types](#document-types)
15. [Subscription Tiers](#subscription-tiers)
16. [Running Tests](#running-tests)
17. [Cost Estimates](#cost-estimates)
18. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
User (Telegram) ──► Telegram Bot API       User (WhatsApp) ──► Meta Cloud API v21.0
                          │                                          │
                    Webhook POST                              Webhook POST
                          │                                          │
                    ┌─────▼──────────────────────────────────────────▼──┐
                    │                    FastAPI                        │
                    │                   app/main                       │
                    │  ◄── Web Dashboard    ◄── Paystack Webhook       │
                    │  ◄── Automation API   ◄── WhatsApp Webhook       │
                    └─────────────────────────┬────────────────────────┘
                                              │
                    ┌─────────────┬───────────┼───────────┬────────────┐
                    │             │           │           │            │
              ┌─────▼──┐   ┌─────▼──┐  ┌─────▼──┐  ┌────▼────┐ ┌────▼────┐
              │  Bot   │   │WhatsApp│  │  API   │  │Payments │ │  Auto  │
              │Handlers│   │ Client │  │ Routes │  │Paystack │ │ mation │
              └─────┬──┘   └─────┬──┘  └─────┬──┘  └────┬────┘ └────┬────┘
                    │             │           │           │            │
                    └─────────────┴───────────┼───────────┴────────────┘
                                              │
                                        ┌─────▼──────┐
                                        │ Claude API │  (AI Engine)
                                        └─────┬──────┘
                                              │
                                        ┌─────▼──────┐
                                        │  Supabase  │  (Postgres + Storage)
                                        └────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Bot framework | python-telegram-bot v21 | Telegram interaction |
| API framework | FastAPI + Uvicorn | Webhook receiver + REST API |
| AI engine | Anthropic Claude (via OpenRouter) | Document generation + business insights |
| Voice transcription | OpenAI Whisper | Voice note to text |
| Database | Supabase (Postgres) | Users, documents, expenses, payments, teams |
| File storage | Supabase Storage | PDF/DOCX files |
| Payments | Paystack | Nigerian subscription billing |
| PDF generation | WeasyPrint | HTML to PDF rendering |
| DOCX generation | python-docx | Word document creation |
| Email | Resend | Transactional emails |
| WhatsApp | Meta Cloud API v21.0 | WhatsApp Business messaging |
| i18n | Custom catalog | English, Pidgin, Yoruba, Hausa |
| Deployment | Railway (Docker) | Production hosting |

---

## Features

### Expense Tracking
- Log expenses via text, quick-parse (`"Fuel 5000"`), or receipt photo (Claude Vision OCR)
- 14 Nigerian-relevant expense categories (Transport, Fuel, Salaries, Rent, Inventory, etc.)
- Monthly/category breakdowns with spending analysis

### Financial Dashboard
- Real-time income vs expenses summary with net profit/loss
- AI-powered natural language queries ("What did I spend on fuel last month?")
- Category breakdown with percentage analysis

### Tax Compliance (FIRS)
- VAT (7.5%), WHT (5%), CIT brackets (Small <N25M 0%, Medium N25M-N100M 20%, Large >N100M 30%)
- Monthly/quarterly tax summaries with filing deadlines
- Save tax records for compliance tracking

### AI Business Insights
- Monthly health score (0-100) with strengths, concerns, and action items
- 3-month spending trend analysis with improvement/decline percentages
- Anomaly detection: category spikes (>2x), large expenses (>30% of total), high expense ratios

### Document Generation
- Professional invoices, proposals, contracts, social media posts, customer replies, business plans
- Nigeria-ready: VAT, Naira formatting, CAC/FIRS compliance, bank detail layouts
- PDF + DOCX output for Pro/Business tiers

### WhatsApp Integration
- Full WhatsApp Business API scaffold (Meta Cloud API v21.0)
- HMAC-SHA256 signature verification for incoming webhooks
- Interactive button menus, template messages, read receipts

### Team Management
- Create teams with business profiles and invite members via secure codes (72-hour expiry)
- Role-based access: Owner, Admin, Member, Accountant, Viewer
- Shared expense/income visibility within teams

### Multi-Language Support (i18n)
- English, Nigerian Pidgin, Yoruba, Hausa
- 20+ translated message keys covering all core flows
- Per-user language preference stored in profile

### Automation API
- n8n-compatible webhook endpoints for scheduled reports
- PDF/DOCX report generation via API
- Trigger dashboards and tax summaries programmatically

---

## Project Structure

```
bizpilot-ng/
├── app/
│   ├── main.py                          # FastAPI app + lifespan
│   ├── core/
│   │   ├── config.py                    # Settings (pydantic-settings)
│   │   ├── constants.py                 # Enums, states, tiers, categories
│   │   └── i18n.py                      # Translations (en/pcm/yo/ha)
│   ├── db/
│   │   └── client.py                    # All Supabase DB operations
│   ├── api/
│   │   └── routes/
│   │       ├── webhooks.py              # Telegram + Paystack webhooks
│   │       ├── dashboard.py             # REST API for web dashboard
│   │       ├── whatsapp.py              # WhatsApp webhook + message handler
│   │       └── automation.py            # n8n automation endpoints
│   ├── bot/
│   │   ├── app.py                       # Bot application builder
│   │   ├── handlers/
│   │   │   ├── common.py                # /start /help /profile /upgrade
│   │   │   ├── invoice.py               # Invoice conversation flow
│   │   │   ├── documents.py             # Proposal/Contract/Social/Reply/BizPlan
│   │   │   ├── expenses.py              # /expense + /scan + receipt OCR
│   │   │   ├── dashboard.py             # /dashboard + AI queries
│   │   │   ├── tax.py                   # /tax compliance handler
│   │   │   ├── insights.py              # /insights AI business analysis
│   │   │   ├── team.py                  # /team management + invitations
│   │   │   └── language.py              # /language selection
│   │   └── keyboards/
│   │       └── menus.py                 # All InlineKeyboardMarkup definitions
│   └── services/
│       ├── ai/
│       │   ├── prompts.py               # Nigerian context prompt library
│       │   └── claude_client.py         # Claude API + Whisper + insights
│       ├── documents/
│       │   ├── generator.py             # PDF/DOCX/text generation
│       │   └── storage.py              # Supabase Storage uploads
│       ├── payments/
│       │   ├── paystack.py              # Paystack API client
│       │   └── email.py                 # Resend email service
│       └── whatsapp/
│           └── client.py                # Meta Cloud API client
├── dashboard/
│   └── index.html                       # Web dashboard (single-file)
├── scripts/
│   ├── 001_initial_schema.sql           # Users, documents, payments
│   ├── 002_expenses_tax_schema.sql      # Expenses, income, tax records
│   ├── 003_teams_schema.sql             # Teams, members, invitations
│   ├── run_dev.py                       # Local development runner
│   └── register_webhook.py             # Production webhook registration
├── tests/
│   ├── test_core_logic.py               # Core logic tests (49 tests)
│   └── test_phase3.py                   # Phase 3 feature tests (43 tests)
├── .env.example                         # Environment variable template
├── requirements.txt                     # Python dependencies
├── Dockerfile                           # Multi-stage production container
├── railway.toml                         # Railway deployment config
├── Procfile                             # Alternative deployment
└── pytest.ini                           # Test configuration
```

---

## Prerequisites

- Python 3.11+
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- An Anthropic API key or OpenRouter key
- A Supabase project (https://supabase.com)
- A Paystack account (https://paystack.com)
- Optional: OpenAI API key (for voice note transcription)
- Optional: Resend account (for email notifications)
- Optional: Meta WhatsApp Business API credentials

---

## Local Development Setup

### 1. Clone and create virtual environment

```bash
git clone https://github.com/yourname/bizpilot-ng.git
cd bizpilot-ng

python -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\activate           # Windows PowerShell

pip install -r requirements.txt
```

### 2. Copy and fill in environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in all values — see the [Environment Variables](#environment-variables) section below.

### 3. Run the database migrations

Go to your Supabase Dashboard, SQL Editor, and run each migration in order:

1. `scripts/001_initial_schema.sql` — Users, documents, payments
2. `scripts/002_expenses_tax_schema.sql` — Expenses, income, tax records
3. `scripts/003_teams_schema.sql` — Teams, members, invitations

### 4. Start the development server

```bash
python scripts/run_dev.py
```

This starts:
- FastAPI on `http://localhost:8000`
- API docs on `http://localhost:8000/docs`
- Web dashboard on `http://localhost:8000/dashboard`
- Telegram bot in polling mode (no webhook needed locally)

---

## Environment Variables

Copy `.env.example` to `.env` and fill in every value:

### Required

| Variable | Where to get it |
|---|---|
| `SECRET_KEY` | Any random 32+ character string |
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_WEBHOOK_SECRET` | Any random string (you choose) |
| `WEBHOOK_BASE_URL` | Your Railway public URL |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) or OpenRouter |
| `ANTHROPIC_BASE_URL` | Default: Anthropic API. Set to `https://openrouter.ai/api` for OpenRouter |
| `SUPABASE_URL` | Supabase Dashboard, Settings, API |
| `SUPABASE_ANON_KEY` | Supabase Dashboard, Settings, API |
| `SUPABASE_SERVICE_KEY` | Supabase Dashboard, Settings, API (service_role) |
| `PAYSTACK_SECRET_KEY` | [Paystack Dashboard](https://dashboard.paystack.com), Settings, API |
| `PAYSTACK_PUBLIC_KEY` | Paystack Dashboard, Settings, API |

### Optional

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Voice note transcription via Whisper |
| `RESEND_API_KEY` | Transactional emails |
| `PAYSTACK_PRO_PLAN_CODE` | Paystack plan code for Pro tier |
| `PAYSTACK_COMMANDER_PLAN_CODE` | Paystack plan code for Business tier (legacy name) |
| `WHATSAPP_ACCESS_TOKEN` | Meta WhatsApp Business API access token |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp Business phone number ID |
| `WHATSAPP_VERIFY_TOKEN` | Webhook verification token (you choose) |
| `WHATSAPP_APP_SECRET` | Meta App secret for HMAC signature verification |

---

## Database Setup (Supabase)

### Step 1 — Run the migrations

In your [Supabase Dashboard](https://supabase.com/dashboard), select your project, go to SQL Editor, and run each file in order:

**Migration 1:** `scripts/001_initial_schema.sql`
- `users` table with subscription tracking
- `documents` table with full document history
- `payments` table with Paystack records
- `increment_docs_used()` and `reset_monthly_doc_counts()` RPC functions
- Row Level Security policies
- `bizpilot-documents` storage bucket

**Migration 2:** `scripts/002_expenses_tax_schema.sql`
- `expenses` table with categories and receipt storage
- `income` table for revenue tracking
- `tax_records` table for FIRS compliance
- Indexes on user_id, date, and category

**Migration 3:** `scripts/003_teams_schema.sql`
- `teams` table with owner and plan
- `team_members` table with roles (owner/admin/member/accountant/viewer)
- `team_invitations` table with invite codes and expiry
- Adds `team_id` column to users, expenses, income tables

### Step 2 — Set up monthly reset cron job

Enable `pg_cron` (Dashboard, Database, Extensions, search `pg_cron`, enable), then run:

```sql
SELECT cron.schedule(
  'reset-monthly-docs',
  '0 0 1 * *',
  'SELECT reset_monthly_doc_counts()'
);
```

### Step 3 — Verify

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public';
-- Should show: users, documents, payments, expenses, income, tax_records, teams, team_members, team_invitations
```

---

## Paystack Setup

### Step 1 — Create subscription plans

In your [Paystack Dashboard](https://dashboard.paystack.com):

1. Go to **Products, Plans**
2. Create **Pro** plan:
   - Name: `BizPilot Pro`
   - Amount: `5000` (N5,000)
   - Interval: Monthly
   - Copy the plan code (e.g. `PLN_xxxxxxxxxx`)
3. Create **Business** plan:
   - Name: `BizPilot Business`
   - Amount: `15000` (N15,000)
   - Interval: Monthly
   - Copy the plan code

### Step 2 — Add plan codes to .env

```env
PAYSTACK_PRO_PLAN_CODE=PLN_xxxxxxxxxx
PAYSTACK_COMMANDER_PLAN_CODE=PLN_xxxxxxxxxx
```

Note: The env var name `PAYSTACK_COMMANDER_PLAN_CODE` is a legacy alias that maps to the Business tier internally.

### Step 3 — Register webhook in Paystack

1. Paystack Dashboard, Settings, API Keys & Webhooks
2. Webhook URL: `https://your-app.railway.app/webhook/paystack`
3. Events to listen for: `charge.success`, `subscription.disable`, `invoice.payment_failed`

---

## Running Locally

```bash
# Development (polling mode — no public URL needed)
python scripts/run_dev.py

# Run tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## Production Deployment (Railway)

### Step 1 — Push to GitHub

```bash
git remote add origin https://github.com/yourname/bizpilot-ng.git
git push -u origin main
```

### Step 2 — Deploy on Railway

1. Go to [railway.app](https://railway.app), New Project, Deploy from GitHub
2. Select your `bizpilot-ng` repository
3. Railway detects the Dockerfile automatically

### Step 3 — Add environment variables on Railway

In Railway, your project, Variables tab, add every variable from your `.env` file.

Set `WEBHOOK_BASE_URL` to your Railway-generated URL:
```
https://bizpilot-ng-production.up.railway.app
```

Set `APP_ENV=production`.

### Step 4 — Register the Telegram webhook

```bash
python scripts/register_webhook.py
```

### Step 5 — Verify deployment

```bash
curl https://your-app.railway.app/
# Expected: {"service":"BizPilot NG","status":"running","version":"1.0.0"}

curl https://your-app.railway.app/api/v1/health
# Expected: {"status":"ok","service":"BizPilot NG API"}
```

---

## Web Dashboard

Access at `https://your-app.railway.app/dashboard`

Login with your Telegram ID (shown via `/profile` in the bot).

**Features:**
- Overview stats (documents used, subscription status, usage bar)
- Full document history with PDF download links
- Business profile editor
- Subscription plan comparison and upgrade flow

---

## Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome + profile setup (new users) or main menu (returning) |
| `/expense` | Log a new expense (amount, category, description) |
| `/scan` | Scan a receipt photo for automatic expense logging |
| `/dashboard` | View financial summary + AI-powered queries |
| `/tax` | Tax compliance: monthly summary, quarterly report, deadlines |
| `/insights` | AI business analysis: health score, trends, anomalies |
| `/team` | Create/join teams, invite members, manage roles |
| `/language` | Switch language (English, Pidgin, Yoruba, Hausa) |
| `/invoice` | Generate a professional invoice |
| `/proposal` | Write a business proposal |
| `/contract` | Create a contract or NDA |
| `/post` | Generate social media content (3 variations) |
| `/reply` | Draft a professional customer reply |
| `/bizplan` | Business plan summary for loans/investors |
| `/profile` | View and update business profile |
| `/upgrade` | View subscription plans and upgrade |
| `/history` | View recent documents |
| `/help` | Show all commands |
| `/cancel` | Cancel the current operation |

**Quick expense:** Type something like `"Fuel 5000"` or `"Lunch 1500"` directly — the bot auto-parses it.

**Receipt OCR:** Send a photo of any receipt — Claude Vision extracts the amount, vendor, and category automatically.

**Voice notes:** Send a voice message — the bot transcribes it via Whisper and routes you to the right flow.

---

## Document Types

| Type | Command | What it generates |
|---|---|---|
| Invoice | `/invoice` | Professional invoice with VAT (7.5%), WHT, bank details |
| Proposal | `/proposal` | Business proposal with deliverables, timeline, investment breakdown |
| Contract | `/contract` | Service agreement, NDA, vendor agreement, or partnership agreement |
| Social Post | `/post` | 3 platform-optimised caption variations with hashtags |
| Customer Reply | `/reply` | Professional response to complaints, inquiries, or orders |
| Business Plan | `/bizplan` | 1-page summary for BOI, NIRSAL, bank loan, or investor applications |

---

## Subscription Tiers

| Feature | Free | Pro (N5,000/mo) | Business (N15,000/mo) | Enterprise |
|---|---|---|---|---|
| Transactions/month | 50 | Unlimited | Unlimited | Unlimited |
| Output format | Text in chat | PDF + DOCX | PDF + DOCX | PDF + DOCX |
| Expense tracking | Yes | Yes | Yes | Yes |
| Tax compliance | Basic | Full | Full | Full |
| AI Insights | No | Yes | Yes | Yes |
| Team seats | 1 | 1 | Up to 10 | Custom |
| Watermark | Yes | No | No | No |
| Custom logo on docs | No | No | Yes | Yes |
| Document history | 30 days | 1 year | 1 year | Unlimited |
| Support | Community | Priority | Dedicated | Dedicated |
| Pricing | Free | N5,000/month | N15,000/month | Contact sales |

---

## Running Tests

92 tests across 2 test files — all run offline with no external service calls.

```bash
# All tests
pytest tests/ -v

# Core logic tests (49 tests)
pytest tests/test_core_logic.py -v

# Phase 3 feature tests (43 tests)
pytest tests/test_phase3.py -v

# Specific test class
pytest tests/test_phase3.py::TestPricingRestructure -v

# With coverage report
pytest tests/ --cov=app --cov-report=term-missing
```

---

## Cost Estimates

Monthly operating costs at 500 paying users:

| Service | Usage | Monthly Cost |
|---|---|---|
| Railway (hosting) | 1 service, ~512MB RAM | ~$5 |
| Anthropic Claude (via OpenRouter) | ~10,000 docs + insights | ~$45 |
| Supabase | Pro tier (if needed) | $25 or free |
| Paystack | 1.5% + N100 per transaction | ~N7,500 |
| OpenAI Whisper | ~500 voice notes x 30s avg | ~$0.50 |
| Resend (email) | ~2,000 emails | Free |
| **Total** | | **~$75-$100/month** |

At 500 Pro subscribers: **N2,500,000/month (~$1,562) MRR**
Operating cost: **~N160,000/month (~$100)**
**Net margin: ~94%**

---

## Troubleshooting

### Bot not responding

1. Check the webhook is registered: `python scripts/register_webhook.py`
2. Check Railway logs for errors
3. Verify `TELEGRAM_BOT_TOKEN` is correct in Railway Variables
4. Confirm `WEBHOOK_BASE_URL` matches your actual Railway URL

### PDF generation failing

WeasyPrint requires system fonts and Cairo. These are included in the Dockerfile. If running locally on Windows, use WSL2 or Docker.

### Paystack webhook not firing

1. Confirm the webhook URL in Paystack Dashboard, Settings, Webhooks
2. Check that `APP_ENV=production` is set
3. Verify the webhook secret matches between Paystack and your `.env`

### Claude API errors

- `AuthenticationError`: Check `ANTHROPIC_API_KEY` is valid
- `RateLimitError`: Handled automatically with retry (up to 3 attempts)
- If using OpenRouter, ensure `ANTHROPIC_BASE_URL=https://openrouter.ai/api`

### Supabase connection errors

- Confirm `SUPABASE_URL` ends with `.supabase.co` (no trailing slash)
- Use the **service_role** key for `SUPABASE_SERVICE_KEY`, not the anon key
- Check Supabase project is not paused (free tier pauses after inactivity)

---

## License

MIT
