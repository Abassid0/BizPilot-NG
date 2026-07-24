-- ================================================================
-- BizPilot Pro — Expenses & Tax Schema Migration
-- File: scripts/002_expenses_tax_schema.sql
--
-- Run this in your Supabase SQL Editor after 001_initial_schema.sql
-- Safe to re-run (uses IF NOT EXISTS).
-- ================================================================


-- ── EXPENSE CATEGORIES ──────────────────────────────────────────

CREATE TABLE IF NOT EXISTS expense_categories (
  id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  name            TEXT          UNIQUE NOT NULL,
  icon            TEXT          DEFAULT '',
  is_system       BOOLEAN       NOT NULL DEFAULT true,
  created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

INSERT INTO expense_categories (name, icon, is_system) VALUES
  ('Transport & Logistics', '', true),
  ('Food & Catering', '', true),
  ('Office Supplies', '', true),
  ('Rent & Utilities', '', true),
  ('Staff & Salaries', '', true),
  ('Marketing & Ads', '', true),
  ('Professional Services', '', true),
  ('Inventory & Stock', '', true),
  ('Equipment & Tools', '', true),
  ('Communication & Internet', '', true),
  ('Insurance', '', true),
  ('Bank Charges & Fees', '', true),
  ('Taxes & Government', '', true),
  ('Miscellaneous', '', true)
ON CONFLICT (name) DO NOTHING;


-- ── EXPENSES ────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS expenses (
  id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  amount          NUMERIC(15,2) NOT NULL,
  description     TEXT          NOT NULL DEFAULT '',
  category        TEXT          NOT NULL DEFAULT 'Miscellaneous',
  vendor          TEXT          DEFAULT '',

  expense_date    DATE          NOT NULL DEFAULT CURRENT_DATE,

  -- OCR receipt data
  receipt_url     TEXT,
  ocr_raw         JSONB         DEFAULT '{}'::jsonb,
  source          TEXT          NOT NULL DEFAULT 'manual'
                                CHECK (source IN ('manual', 'ocr', 'csv_import', 'voice')),

  -- For bank reconciliation
  is_reconciled   BOOLEAN       NOT NULL DEFAULT false,
  bank_ref        TEXT,

  created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_expenses_user_id
  ON expenses (user_id);

CREATE INDEX IF NOT EXISTS idx_expenses_category
  ON expenses (category);

CREATE INDEX IF NOT EXISTS idx_expenses_date
  ON expenses (expense_date DESC);

CREATE INDEX IF NOT EXISTS idx_expenses_user_date
  ON expenses (user_id, expense_date DESC);

-- Auto-update updated_at
DROP TRIGGER IF EXISTS expenses_updated_at ON expenses;
CREATE TRIGGER expenses_updated_at
  BEFORE UPDATE ON expenses
  FOR EACH ROW
  EXECUTE FUNCTION set_updated_at();


-- ── TAX RECORDS ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS tax_records (
  id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  tax_type        TEXT          NOT NULL
                                CHECK (tax_type IN ('vat', 'wht', 'cit', 'paye')),
  period_start    DATE          NOT NULL,
  period_end      DATE          NOT NULL,

  gross_amount    NUMERIC(15,2) NOT NULL DEFAULT 0,
  tax_amount      NUMERIC(15,2) NOT NULL DEFAULT 0,
  status          TEXT          NOT NULL DEFAULT 'calculated'
                                CHECK (status IN ('calculated', 'filed', 'paid')),

  details         JSONB         DEFAULT '{}'::jsonb,

  due_date        DATE,
  filed_at        TIMESTAMPTZ,
  created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tax_records_user_id
  ON tax_records (user_id);

CREATE INDEX IF NOT EXISTS idx_tax_records_period
  ON tax_records (user_id, period_start, period_end);


-- ── INCOME (from invoices) ──────────────────────────────────────
-- Track income separately for P&L calculations

CREATE TABLE IF NOT EXISTS income (
  id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  amount          NUMERIC(15,2) NOT NULL,
  description     TEXT          NOT NULL DEFAULT '',
  client_name     TEXT          DEFAULT '',
  category        TEXT          NOT NULL DEFAULT 'Services',

  income_date     DATE          NOT NULL DEFAULT CURRENT_DATE,
  invoice_id      UUID          REFERENCES documents(id) ON DELETE SET NULL,

  is_received     BOOLEAN       NOT NULL DEFAULT false,

  created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_income_user_id
  ON income (user_id);

CREATE INDEX IF NOT EXISTS idx_income_user_date
  ON income (user_id, income_date DESC);


-- ── AUTOMATION WEBHOOKS ─────────────────────────────────────────
-- Track n8n webhook registrations

CREATE TABLE IF NOT EXISTS automation_webhooks (
  id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  webhook_type    TEXT          NOT NULL
                                CHECK (webhook_type IN (
                                  'weekly_report', 'monthly_report',
                                  'tax_reminder', 'low_balance', 'custom'
                                )),
  webhook_url     TEXT          NOT NULL,
  is_active       BOOLEAN       NOT NULL DEFAULT true,
  last_fired_at   TIMESTAMPTZ,

  created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_automation_user_id
  ON automation_webhooks (user_id);


-- ── RLS ─────────────────────────────────────────────────────────

ALTER TABLE expenses            ENABLE ROW LEVEL SECURITY;
ALTER TABLE tax_records         ENABLE ROW LEVEL SECURITY;
ALTER TABLE income              ENABLE ROW LEVEL SECURITY;
ALTER TABLE expense_categories  ENABLE ROW LEVEL SECURITY;
ALTER TABLE automation_webhooks ENABLE ROW LEVEL SECURITY;


-- ── HELPER FUNCTIONS ────────────────────────────────────────────

CREATE OR REPLACE FUNCTION get_monthly_expense_summary(
  p_user_id UUID,
  p_year INTEGER DEFAULT EXTRACT(YEAR FROM NOW()),
  p_month INTEGER DEFAULT EXTRACT(MONTH FROM NOW())
)
RETURNS TABLE(category TEXT, total NUMERIC, count BIGINT) AS $$
BEGIN
  RETURN QUERY
  SELECT
    e.category,
    SUM(e.amount) as total,
    COUNT(*) as count
  FROM expenses e
  WHERE e.user_id = p_user_id
    AND EXTRACT(YEAR FROM e.expense_date) = p_year
    AND EXTRACT(MONTH FROM e.expense_date) = p_month
  GROUP BY e.category
  ORDER BY total DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


CREATE OR REPLACE FUNCTION get_monthly_income_summary(
  p_user_id UUID,
  p_year INTEGER DEFAULT EXTRACT(YEAR FROM NOW()),
  p_month INTEGER DEFAULT EXTRACT(MONTH FROM NOW())
)
RETURNS TABLE(category TEXT, total NUMERIC, count BIGINT) AS $$
BEGIN
  RETURN QUERY
  SELECT
    i.category,
    SUM(i.amount) as total,
    COUNT(*) as count
  FROM income i
  WHERE i.user_id = p_user_id
    AND EXTRACT(YEAR FROM i.income_date) = p_year
    AND EXTRACT(MONTH FROM i.income_date) = p_month
  GROUP BY i.category
  ORDER BY total DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- ── VERIFY ──────────────────────────────────────────────────────

SELECT
  table_name,
  (SELECT COUNT(*) FROM information_schema.columns c
   WHERE c.table_name = t.table_name
   AND c.table_schema = 'public') AS column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
  AND table_name IN ('expenses', 'tax_records', 'income', 'expense_categories', 'automation_webhooks')
ORDER BY table_name;
