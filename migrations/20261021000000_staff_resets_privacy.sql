-- Migration: staff accounts with roles, staff-issued password reset codes,
-- and account deletion support. Additive and re-runnable. `activation` only.

CREATE TABLE IF NOT EXISTS activation.staff (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name          text NOT NULL,
    email         text NOT NULL,
    password_hash text NOT NULL,
    role          text NOT NULL CHECK (role IN ('admin', 'finance', 'field', 'support')),
    active        boolean NOT NULL DEFAULT true,
    created_at    timestamptz NOT NULL DEFAULT now(),
    last_login_at timestamptz
);

CREATE UNIQUE INDEX IF NOT EXISTS staff_email_ci_unique ON activation.staff (lower(email));

-- One-time codes that staff create after verifying who is asking (phone call,
-- in person). Only a hash is stored; the code is shown to staff once.
CREATE TABLE IF NOT EXISTS activation.password_resets (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    account_type text NOT NULL CHECK (account_type IN ('youth', 'business')),
    account_id   uuid NOT NULL,
    code_hash    text NOT NULL,
    expires_at   timestamptz NOT NULL,
    used_at      timestamptz,
    attempts     integer NOT NULL DEFAULT 0,
    created_by   text NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_password_resets_account
    ON activation.password_resets (account_type, account_id, created_at DESC);

-- A deleted account keeps its financial/work records but loses personal data.
ALTER TABLE activation.youth ADD COLUMN IF NOT EXISTS deleted_at timestamptz;

ALTER TABLE activation.staff ENABLE ROW LEVEL SECURITY;
ALTER TABLE activation.password_resets ENABLE ROW LEVEL SECURITY;
