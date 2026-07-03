# BizPilot NG 🇳🇬

**AI-powered business document assistant for Nigerian entrepreneurs and SMEs.**

Generate professional invoices, proposals, contracts, social media content, customer replies, and business plan summaries — directly from Telegram — in under 60 seconds. All documents are Nigeria-ready: correct VAT (7.5%), Naira formatting, CAC/FIRS compliance, and Nigerian bank detail layouts.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Prerequisites](#prerequisites)
5. [Local Development Setup](#local-development-setup)
6. [Environment Variables](#environment-variables)
7. [Database Setup (Supabase)](#database-setup-supabase)
8. [Paystack Setup](#paystack-setup)
9. [Running Locally](#running-locally)
10. [Production Deployment (Railway)](#production-deployment-railway)
11. [Web Dashboard](#web-dashboard)
12. [Bot Commands](#bot-commands)
13. [Document Types](#document-types)
14. [Subscription Tiers](#subscription-tiers)
15. [Running Tests](#running-tests)
16. [Cost Estimates](#cost-estimates)
17. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
User (Telegram) ──► Telegram Bot API
                          │
                    Webhook POST
                          │
                    ┌─────▼──────┐
                    │  FastAPI   │  ◄── Web Dashboard (HTML/JS)
                    │  app/main  │  ◄── Paystack Webhook
                    └─────┬──────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
        ┌─────▼──┐  ┌─────▼──┐  ┌────▼────┐
        │  Bot   │  │  API   │  │Payments │
        │Handlers│  │ Routes │  │Paystack │
        └─────┬──┘  └─────┬──┘  └────┬────┘
              │           │           │
              └───────────┼───────────┘
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
| AI engine | Anthropic Claude Sonnet | Document generation |
| Voice transcription | OpenAI Whisper | Voice note → text |
| Database | Supabase (Postgres) | Users, documents, payments |
| File storage | Supabase Storage | PDF/DOCX files |
| Payments | Paystack | Nigerian subscription billing |
| PDF generation | WeasyPrint | HTML → PDF rendering |
| DOCX generation | python-docx | Word document creation |
| Email | Resend | Transactional emails |
| Deployment | Railway | Production hosting |

---

## Project Structure

```
bizpilot-ng/
├── app/
│   ├── main.py                      # FastAPI app + lifespan
│   ├── core/
│   │   ├── config.py                # Settings (pydantic-settings)
│   │   └── constants.py             # Enums, states, messages
│   ├── db/
│   │   └── client.py                # All Supabase DB operations
│   ├── api/
│   │   └── routes/
│   │       ├── webhooks.py          # Telegram + Paystack webhooks
│   │       └── dashboard.py         # REST API for web dashboard
│   ├── bot/
│   │   ├── app.py                   # Bot application builder
│   │   ├── handlers/
│   │   │   ├── common.py            # /start /help /profile /upgrade
│   │   │   ├── invoice.py           # Invoice conversation flow
│   │   │   └── documents.py         # Proposal/Contract/Social/Reply/BizPlan
│   │   └── keyboards/
│   │       └── menus.py             # All InlineKeyboardMarkup definitions
│   └── services/
│       ├── ai/
│       │   ├── prompts.py           # Nigerian context prompt library
│       │   └── claude_client.py     # Claude API + Whisper
│       ├── documents/
│       │   ├── generator.py         # PDF/DOCX/text generation
│       │   └── storage.py           # Supabase Storage uploads
│       └── payments/
│           ├── paystack.py          # Paystack API client
│           └── email.py             # Resend email service
├── dashboard/
│   └── index.html                   # Web dashboard (single-file)
├── scripts/
│   ├── 001_initial_schema.sql       # Supabase migration
│   ├── run_dev.py                   # Local development runner
│   └── register_webhook.py          # Production webhook registration
├── tests/
│   └── test_core_logic.py           # Unit tests (no external calls)
├── .env.example                     # Environment variable template
├── requirements.txt                 # Python dependencies
├── Dockerfile                       # Production container
├── railway.toml                     # Railway deployment config
├── Procfile                         # Render.com alternative
└── pytest.ini                       # Test configuration
```

---

## Prerequisites

- Python 3.11+
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- An Anthropic API key (https://console.anthropic.com)
- A Supabase project (https://supabase.com — free tier works)
- A Paystack account (https://paystack.com — Nigerian business)
- Optional: OpenAI API key (for voice note transcription)
- Optional: Resend account (for email notifications)

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

### 3. Run the database migration

Go to your Supabase Dashboard → SQL Editor → paste and run the contents of `scripts/001_initial_schema.sql`.

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
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) → /newbot |
| `TELEGRAM_WEBHOOK_SECRET` | Any random string (you choose) |
| `WEBHOOK_BASE_URL` | Your Railway/Render public URL |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| `SUPABASE_URL` | Supabase Dashboard → Settings → API |
| `SUPABASE_ANON_KEY` | Supabase Dashboard → Settings → API |
| `SUPABASE_SERVICE_KEY` | Supabase Dashboard → Settings → API (service_role) |
| `PAYSTACK_SECRET_KEY` | [Paystack Dashboard](https://dashboard.paystack.com) → Settings → API |
| `PAYSTACK_PUBLIC_KEY` | Paystack Dashboard → Settings → API |

### Optional but recommended

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Voice note transcription via Whisper |
| `RESEND_API_KEY` | Transactional emails |
| `PAYSTACK_PRO_PLAN_CODE` | Paystack plan code for Pro tier |
| `PAYSTACK_COMMANDER_PLAN_CODE` | Paystack plan code for Commander tier |

---

## Database Setup (Supabase)

### Step 1 — Run the migration

1. Go to your [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project → SQL Editor
3. Paste the full contents of `scripts/001_initial_schema.sql`
4. Click **Run**

This creates:
- `users` table with subscription tracking
- `documents` table with full document history
- `payments` table with Paystack records
- `increment_docs_used()` RPC function
- `reset_monthly_doc_counts()` RPC function
- Row Level Security policies
- The `bizpilot-documents` storage bucket

### Step 2 — Set up monthly reset cron job

In Supabase SQL Editor, enable `pg_cron` (Dashboard → Database → Extensions → search `pg_cron` → enable), then run:

```sql
SELECT cron.schedule(
  'reset-monthly-docs',
  '0 0 1 * *',
  'SELECT reset_monthly_doc_counts()'
);
```

This resets all users' `docs_used` counter to 0 on the 1st of every month.

### Step 3 — Verify

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public';
-- Should show: users, documents, payments
```

---

## Paystack Setup

### Step 1 — Create subscription plans

In your [Paystack Dashboard](https://dashboard.paystack.com):

1. Go to **Products → Plans**
2. Create **Pro Operator** plan:
   - Name: `BizPilot NG Pro`
   - Amount: `4999` (₦4,999)
   - Interval: Monthly
   - Copy the plan code (e.g. `PLN_xxxxxxxxxx`)
3. Create **Business Commander** plan:
   - Name: `BizPilot NG Commander`
   - Amount: `12999` (₦12,999)
   - Interval: Monthly
   - Copy the plan code

### Step 2 — Add plan codes to .env

```env
PAYSTACK_PRO_PLAN_CODE=PLN_xxxxxxxxxx
PAYSTACK_COMMANDER_PLAN_CODE=PLN_xxxxxxxxxx
```

### Step 3 — Register webhook in Paystack

1. Paystack Dashboard → Settings → API Keys & Webhooks
2. Webhook URL: `https://your-app.railway.app/webhook/paystack`
3. Events to listen for: `charge.success`, `subscription.disable`, `invoice.payment_failed`

---

## Running Locally

```bash
# Development (polling mode — no public URL needed)
python scripts/run_dev.py

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## Production Deployment (Railway)

### Step 1 — Push to GitHub

```bash
git init
git add .
git commit -m "Initial BizPilot NG commit"
git remote add origin https://github.com/yourname/bizpilot-ng.git
git push -u origin main
```

### Step 2 — Deploy on Railway

1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
2. Select your `bizpilot-ng` repository
3. Railway detects the Dockerfile automatically

### Step 3 — Add environment variables on Railway

In Railway → your project → Variables tab, add every variable from your `.env` file.

Set `WEBHOOK_BASE_URL` to your Railway-generated URL, e.g.:
```
https://bizpilot-ng-production.up.railway.app
```

Set `APP_ENV=production`.

### Step 4 — Register the Telegram webhook

After the app is live and running on Railway:

```bash
# From your local machine (with .env updated to production URL)
python scripts/register_webhook.py
```

Expected output:
```
Bot: @YourBotUsername (ID: 123456789)
Webhook URL: https://your-app.railway.app/webhook/telegram/your-secret

✓ Existing webhook deleted
✓ Webhook registered successfully

Webhook Info:
  URL:               https://your-app.railway.app/webhook/telegram/your-secret
  Pending updates:   0
  Last error:        None

✅ Done. Your bot is live!
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

The web dashboard is a single HTML file served by FastAPI at `/dashboard`.

**Access:** `https://your-app.railway.app/dashboard`

**Login:** Users enter their Telegram ID (shown in the bot via `/profile`).

**Features:**
- Overview stats (documents used, subscription status, usage bar)
- Full document history with PDF download links
- Business profile editor (updates documents automatically)
- Subscription plan comparison and upgrade flow

**Finding your Telegram ID:** Open the bot in Telegram and type `/profile` — your ID is displayed in the profile summary.

---

## Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome + profile setup (new users) or main menu (returning) |
| `/invoice` | Generate a professional invoice |
| `/proposal` | Write a business proposal |
| `/contract` | Create a contract or NDA |
| `/post` | Generate social media content (3 variations) |
| `/reply` | Draft a professional customer reply |
| `/bizplan` | Write a business plan summary for loans/investors |
| `/profile` | View and update business profile |
| `/upgrade` | View subscription plans and upgrade |
| `/history` | View recent documents |
| `/help` | Show all commands |
| `/cancel` | Cancel the current operation |

**Voice notes:** Send a voice message in any language — the bot transcribes it via Whisper and routes you to the right document type.

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

| Feature | Free (Starter) | Pro (₦4,999/mo) | Commander (₦12,999/mo) |
|---|---|---|---|
| Documents/month | 5 | Unlimited | Unlimited |
| Output format | Text in chat | PDF + DOCX | PDF + DOCX |
| Watermark | Yes | No | No |
| Team seats | 1 | 1 | 3 |
| Custom logo on docs | No | No | Yes |
| Document history | 30 days | 1 year | 1 year |
| Support | Community | Priority | Dedicated |

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test class
pytest tests/test_core_logic.py::TestParseItems -v

# Specific test
pytest tests/test_core_logic.py::TestNigerianTax::test_vat_rate_is_seven_point_five_percent -v

# With coverage report
pytest tests/ --cov=app --cov-report=term-missing
```

Tests in `tests/test_core_logic.py` require **no external services** — they test pure logic only (parsers, formatters, utilities, prompt factory). They run offline.

---

## Cost Estimates

Monthly operating costs at 500 paying users:

| Service | Usage | Monthly Cost |
|---|---|---|
| Railway (hosting) | 1 service, ~512MB RAM | ~$5 |
| Anthropic Claude Sonnet | ~10,000 docs × avg 1,500 tokens | ~$45 |
| Supabase | Pro tier (if needed) | $25 or free |
| Paystack | 1.5% + ₦100 per transaction | ~₦7,500 |
| OpenAI Whisper | ~500 voice notes × 30s avg | ~$0.50 |
| Resend (email) | ~2,000 emails | Free |
| **Total** | | **~$75–$100/month** |

At 500 Pro subscribers: **₦2,499,500/month (~$1,562) MRR**
Operating cost: **~₦160,000/month (~$100)**
**Net margin: ~94%**

---

## Troubleshooting

### Bot not responding

1. Check the webhook is registered: `python scripts/register_webhook.py`
2. Check Railway logs for errors
3. Verify `TELEGRAM_BOT_TOKEN` is correct in Railway Variables
4. Confirm `WEBHOOK_BASE_URL` matches your actual Railway URL exactly

### "User not found" in dashboard

The user must start the Telegram bot first with `/start`. The dashboard login uses the Telegram ID which is only created when `/start` is sent.

### PDF generation failing

WeasyPrint requires system fonts and Cairo. These are included in the Dockerfile. If running locally on Windows, WeasyPrint may be difficult to install — use WSL2 or Docker.

### Paystack webhook not firing

1. Confirm the webhook URL is correct in Paystack Dashboard → Settings → Webhooks
2. Check that `APP_ENV=production` is set (dev mode rejects webhooks)
3. Verify the webhook secret matches between Paystack and your `.env`

### Claude API errors

- `AuthenticationError`: Check `ANTHROPIC_API_KEY` is valid
- `RateLimitError`: Handled automatically with retry (up to 3 attempts)
- `APIConnectionError`: Transient network issue — retried automatically

### Supabase connection errors

- Confirm `SUPABASE_URL` ends with `.supabase.co` (no trailing slash)
- Use the **service_role** key for `SUPABASE_SERVICE_KEY`, not the anon key
- Check Supabase project is not paused (free tier pauses after inactivity)

To unpause: Supabase Dashboard → your project → click **Restore project**

---

## Support

- Telegram bot: [@YourBotUsername](https://t.me/YourBotUsername)
- Email: support@bizpilot.ng
- Dashboard: https://your-app.railway.app/dashboard
