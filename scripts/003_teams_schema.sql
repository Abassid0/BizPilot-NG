-- ================================================================
-- BizPilot Pro — Teams & Multi-User Schema Migration
-- File: scripts/003_teams_schema.sql
--
-- Run this in your Supabase SQL Editor after 002_expenses_tax_schema.sql
-- Safe to re-run (uses IF NOT EXISTS).
-- ================================================================


-- ── TEAMS ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS teams (
  id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  name            TEXT          NOT NULL,
  business_name   TEXT          DEFAULT '',
  owner_id        UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  plan            TEXT          NOT NULL DEFAULT 'free'
                                CHECK (plan IN ('free', 'pro', 'business', 'enterprise')),
  max_members     INTEGER       NOT NULL DEFAULT 1,

  created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_teams_owner_id ON teams (owner_id);


-- ── TEAM MEMBERS ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS team_members (
  id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id         UUID          NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  user_id         UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  role            TEXT          NOT NULL DEFAULT 'member'
                                CHECK (role IN ('owner', 'admin', 'member', 'accountant', 'viewer')),
  invited_by      UUID          REFERENCES users(id) ON DELETE SET NULL,

  joined_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

  UNIQUE (team_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_team_members_team_id ON team_members (team_id);
CREATE INDEX IF NOT EXISTS idx_team_members_user_id ON team_members (user_id);


-- ── TEAM INVITATIONS ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS team_invitations (
  id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id         UUID          NOT NULL REFERENCES teams(id) ON DELETE CASCADE,

  invite_code     TEXT          UNIQUE NOT NULL,
  role            TEXT          NOT NULL DEFAULT 'member'
                                CHECK (role IN ('admin', 'member', 'accountant', 'viewer')),

  invited_email   TEXT          DEFAULT '',
  invited_phone   TEXT          DEFAULT '',

  status          TEXT          NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending', 'accepted', 'expired', 'revoked')),
  expires_at      TIMESTAMPTZ   NOT NULL,

  created_by      UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  accepted_by     UUID          REFERENCES users(id) ON DELETE SET NULL,

  created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_team_invitations_code ON team_invitations (invite_code);
CREATE INDEX IF NOT EXISTS idx_team_invitations_team_id ON team_invitations (team_id);


-- ── Add team_id to users ────────────────────────────────────────

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'team_id'
  ) THEN
    ALTER TABLE users ADD COLUMN team_id UUID REFERENCES teams(id) ON DELETE SET NULL;
    CREATE INDEX idx_users_team_id ON users (team_id);
  END IF;
END $$;


-- ── Add team_id to expenses ─────────────────────────────────────

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'expenses' AND column_name = 'team_id'
  ) THEN
    ALTER TABLE expenses ADD COLUMN team_id UUID REFERENCES teams(id) ON DELETE SET NULL;
    CREATE INDEX idx_expenses_team_id ON expenses (team_id);
  END IF;
END $$;


-- ── Add team_id to income ───────────────────────────────────────

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'income' AND column_name = 'team_id'
  ) THEN
    ALTER TABLE income ADD COLUMN team_id UUID REFERENCES teams(id) ON DELETE SET NULL;
    CREATE INDEX idx_income_team_id ON income (team_id);
  END IF;
END $$;


-- ── RLS ─────────────────────────────────────────────────────────

ALTER TABLE teams            ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_members     ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_invitations ENABLE ROW LEVEL SECURITY;


-- ── Updated triggers ────────────────────────────────────────────

DROP TRIGGER IF EXISTS teams_updated_at ON teams;
CREATE TRIGGER teams_updated_at
  BEFORE UPDATE ON teams
  FOR EACH ROW
  EXECUTE FUNCTION set_updated_at();


-- ── VERIFY ──────────────────────────────────────────────────────

SELECT
  table_name,
  (SELECT COUNT(*) FROM information_schema.columns c
   WHERE c.table_name = t.table_name
   AND c.table_schema = 'public') AS column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
  AND table_name IN ('teams', 'team_members', 'team_invitations')
ORDER BY table_name;
