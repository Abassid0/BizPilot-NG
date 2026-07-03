-- ================================================================
-- BizPilot NG — Supabase Database Migration
-- File: scripts/001_initial_schema.sql
--
-- Run this in your Supabase SQL Editor (Dashboard → SQL Editor)
-- Run once on a fresh project. Safe to re-run (uses IF NOT EXISTS).
-- ================================================================


-- ── Enable required extensions ──────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- ── USERS ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
  id                UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_id       BIGINT        UNIQUE NOT NULL,
  full_name         TEXT,
  username          TEXT,
  email             TEXT,

  -- Subscription
  subscription      TEXT          NOT NULL DEFAULT 'free'
                                  CHECK (subscription IN ('free', 'pro', 'commander')),
  docs_used         INTEGER       NOT NULL DEFAULT 0,
  docs_limit        INTEGER       NOT NULL DEFAULT 5,
  sub_expires_at    TIMESTAMPTZ,

  -- Business profile stored as JSONB for flexibility
  -- Keys: business_name, business_type, industry, cac_number,
  --       tin_number, bank_name, account_number, account_name,
  --       address, logo_url
  business_profile  JSONB         DEFAULT '{}'::jsonb,

  created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- Index for fast telegram_id lookups (most common query)
CREATE INDEX IF NOT EXISTS idx_users_telegram_id
  ON users (telegram_id);

-- Index for subscription status queries
CREATE INDEX IF NOT EXISTS idx_users_subscription
  ON users (subscription);


-- ── DOCUMENTS ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
  id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  doc_type        TEXT          NOT NULL
                                CHECK (doc_type IN (
                                  'invoice', 'proposal', 'contract',
                                  'social_post', 'reply', 'business_plan'
                                )),

  -- Raw input data collected from the user conversation
  input_data      JSONB         DEFAULT '{}'::jsonb,

  -- Claude's raw text output (for audit / regeneration)
  output_text     TEXT,

  -- Supabase Storage signed URL to the PDF/DOCX file
  file_url        TEXT,

  -- Output format delivered to the user
  output_format   TEXT          NOT NULL DEFAULT 'text'
                                CHECK (output_format IN ('pdf', 'docx', 'text')),

  created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- Index for user document history queries
CREATE INDEX IF NOT EXISTS idx_documents_user_id
  ON documents (user_id);

-- Index for filtering by document type
CREATE INDEX IF NOT EXISTS idx_documents_doc_type
  ON documents (doc_type);

-- Index for date-sorted queries
CREATE INDEX IF NOT EXISTS idx_documents_created_at
  ON documents (created_at DESC);


-- ── PAYMENTS ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS payments (
  id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  paystack_ref    TEXT          UNIQUE NOT NULL,
  amount_kobo     INTEGER       NOT NULL,   -- 100 kobo = ₦1
  plan            TEXT          NOT NULL,   -- 'pro' | 'commander'
  status          TEXT          NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending', 'success', 'failed')),

  paid_at         TIMESTAMPTZ,
  created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payments_user_id
  ON payments (user_id);

CREATE INDEX IF NOT EXISTS idx_payments_paystack_ref
  ON payments (paystack_ref);

CREATE INDEX IF NOT EXISTS idx_payments_status
  ON payments (status);


-- ── UPDATED_AT TRIGGER ───────────────────────────────────────────
-- Automatically update the updated_at column on users

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS users_updated_at ON users;
CREATE TRIGGER users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW
  EXECUTE FUNCTION set_updated_at();


-- ── INCREMENT DOCS USED FUNCTION ────────────────────────────────
-- Called by the Python app after each document generation.
-- Using an RPC function prevents race conditions vs. a read-then-write.

CREATE OR REPLACE FUNCTION increment_docs_used(p_telegram_id BIGINT)
RETURNS VOID AS $$
BEGIN
  UPDATE users
  SET docs_used = docs_used + 1
  WHERE telegram_id = p_telegram_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- ── MONTHLY RESET FUNCTION ───────────────────────────────────────
-- Call this via a Supabase cron job (pg_cron) on the 1st of each month.
-- Dashboard → Database → Extensions → enable pg_cron, then:
--
--   SELECT cron.schedule(
--     'reset-monthly-docs',
--     '0 0 1 * *',
--     'SELECT reset_monthly_doc_counts()'
--   );

CREATE OR REPLACE FUNCTION reset_monthly_doc_counts()
RETURNS VOID AS $$
BEGIN
  UPDATE users
  SET docs_used = 0
  WHERE subscription = 'free';
  -- Pro/Commander users: reset to 0 as well (their limit is effectively ∞)
  UPDATE users
  SET docs_used = 0
  WHERE subscription IN ('pro', 'commander');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- ── ROW LEVEL SECURITY ───────────────────────────────────────────
-- We use the service role key server-side, which bypasses RLS.
-- RLS is still enabled as a defence-in-depth measure.

ALTER TABLE users     ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments  ENABLE ROW LEVEL SECURITY;

-- Service role bypasses all RLS — no policies needed for server access.
-- If you add a frontend that uses the anon key directly, add policies here.


-- ── STORAGE BUCKET ───────────────────────────────────────────────
-- Run this separately in the Supabase SQL Editor.
-- Creates the storage bucket for generated documents.

INSERT INTO storage.buckets (id, name, public)
VALUES ('bizpilot-documents', 'bizpilot-documents', false)
ON CONFLICT (id) DO NOTHING;

-- Allow the service role to read/write (server-side uploads)
-- No public access — all downloads go through signed URLs


-- ── VERIFY SCHEMA ────────────────────────────────────────────────
-- Run this after the migration to confirm everything was created:

SELECT
  table_name,
  (SELECT COUNT(*) FROM information_schema.columns c
   WHERE c.table_name = t.table_name
   AND c.table_schema = 'public') AS column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
  AND table_name IN ('users', 'documents', 'payments')
ORDER BY table_name;
