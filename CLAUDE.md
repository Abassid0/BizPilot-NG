# BizPilot Pro

Upgrading `bizpilot-ng` into an investor-ready AI business operations platform for African SMBs.

## Project Context

This is the #1 priority portfolio build (scored 8.8/10 across all evaluation criteria). Goal: transform existing MVP into a deployable, investor-demo-ready product.

## Build Priorities (in order)

1. AI Document Processing — receipt/invoice scanning, OCR, auto-categorization
2. Financial Dashboard — P&L, cash flow, balance sheet with natural language queries
3. Tax Compliance — FIRS VAT/CIT calculations, filing reminders, withholding tax
4. Expense Tracking — Telegram-native logging, bank statement import, reconciliation
5. Business Insights — AI-generated weekly/monthly health reports, anomaly detection
6. Multi-channel — Telegram (primary), WhatsApp Business API, web dashboard (Next.js)

## Tech Stack

- Backend: Python/FastAPI
- Database: Supabase (PostgreSQL + Auth + Storage)
- Payments: Paystack (subscriptions)
- Deployment: Railway
- AI: Claude API (document analysis, insights)
- Bot: python-telegram-bot / WhatsApp Business API
- Automation: n8n (scheduled reports, reminders)
- Frontend: Next.js (web dashboard, later phase)

## Revenue Model

- Free: 50 txns/month, basic categorization
- Pro: N5,000/month — unlimited txns, tax compliance, insights
- Business: N15,000/month — multi-user, accountant access, API
- Enterprise: Custom — white-label for accounting firms

## Investor Pitch

"Xero for Africa, but AI-native and messaging-first. 41M addressable SMBs, $0 CAC through Telegram virality, 90%+ gross margins."

## Competitive Moat

- No AI-native competitor in Nigerian SMB space
- Local tax rules (FIRS), Naira-first, pidgin/Yoruba support
- Telegram-native (where users already are), Paystack-integrated
