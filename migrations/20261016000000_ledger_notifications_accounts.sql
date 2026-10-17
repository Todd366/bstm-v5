-- Migration: ledger_notifications_accounts. Additive and re-runnable.
-- Touches only the `activation` schema.
--
-- 1. Payments ledger: invoices (what a business owes), payments (money in,
--    manually confirmed today, gateway-ready), payouts (money out to youth),
--    payout accounts (where a youth wants to be paid).
-- 2. Notifications (in-app).
-- 3. Youth profile fields (bio, opt-in public profile).
-- 4. Business accounts (login) and job approval by staff.

CREATE SEQUENCE IF NOT EXISTS activation.invoice_ref_seq START 1000;

CREATE TABLE IF NOT EXISTS activation.invoices (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    reference      text NOT NULL UNIQUE,
    business_id    uuid NOT NULL REFERENCES activation.businesses(id),
    opportunity_id uuid REFERENCES activation.opportunities(id),
    assignment_id  uuid REFERENCES activation.opportunity_assignments(id),
    youth_id       uuid REFERENCES activation.youth(id),
    amount         numeric(12,2) NOT NULL CHECK (amount > 0),
    youth_share    numeric(12,2) NOT NULL CHECK (youth_share >= 0),
    platform_share numeric(12,2) NOT NULL CHECK (platform_share >= 0),
    currency       text NOT NULL DEFAULT 'BWP',
    status         text NOT NULL DEFAULT 'Issued'
        CHECK (status IN ('Issued', 'Paid', 'Void')),
    created_at     timestamptz NOT NULL DEFAULT now(),
    paid_at        timestamptz
);

-- One invoice per completed assignment.
CREATE UNIQUE INDEX IF NOT EXISTS invoices_one_per_assignment
    ON activation.invoices (assignment_id) WHERE assignment_id IS NOT NULL AND status <> 'Void';
CREATE INDEX IF NOT EXISTS idx_invoices_business ON activation.invoices (business_id, created_at DESC);

CREATE TABLE IF NOT EXISTS activation.payments (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id      uuid NOT NULL REFERENCES activation.invoices(id),
    amount          numeric(12,2) NOT NULL CHECK (amount > 0),
    method          text NOT NULL
        CHECK (method IN ('MyZaka', 'OrangeMoney', 'BankEFT', 'Cash', 'Card', 'Other')),
    provider        text NOT NULL DEFAULT 'manual',
    provider_ref    text,
    idempotency_key text UNIQUE,
    status          text NOT NULL DEFAULT 'Submitted'
        CHECK (status IN ('Submitted', 'Confirmed', 'Rejected')),
    submitted_by    text NOT NULL DEFAULT 'staff',
    confirmed_by    text,
    note            text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    confirmed_at    timestamptz
);

-- The same transaction reference can never be claimed twice per provider.
CREATE UNIQUE INDEX IF NOT EXISTS payments_provider_ref_unique
    ON activation.payments (provider, provider_ref)
    WHERE provider_ref IS NOT NULL AND status <> 'Rejected';
CREATE INDEX IF NOT EXISTS idx_payments_invoice ON activation.payments (invoice_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON activation.payments (status, created_at);

CREATE TABLE IF NOT EXISTS activation.payout_accounts (
    youth_id     uuid PRIMARY KEY REFERENCES activation.youth(id) ON DELETE CASCADE,
    method       text NOT NULL CHECK (method IN ('MyZaka', 'OrangeMoney', 'BankEFT', 'Other')),
    account_name text NOT NULL,
    account_ref  text NOT NULL,
    updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS activation.payouts (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    youth_id        uuid NOT NULL REFERENCES activation.youth(id),
    invoice_id      uuid NOT NULL REFERENCES activation.invoices(id),
    amount          numeric(12,2) NOT NULL CHECK (amount > 0),
    method          text,
    destination     text,
    provider        text NOT NULL DEFAULT 'manual',
    provider_ref    text,
    status          text NOT NULL DEFAULT 'Pending'
        CHECK (status IN ('Pending', 'Paid', 'Failed')),
    created_at      timestamptz NOT NULL DEFAULT now(),
    paid_at         timestamptz,
    paid_by         text
);

-- At most one live payout per invoice.
CREATE UNIQUE INDEX IF NOT EXISTS payouts_one_per_invoice
    ON activation.payouts (invoice_id) WHERE status <> 'Failed';
CREATE INDEX IF NOT EXISTS idx_payouts_youth ON activation.payouts (youth_id, created_at DESC);

CREATE TABLE IF NOT EXISTS activation.notifications (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_type text NOT NULL CHECK (recipient_type IN ('youth', 'business')),
    recipient_id   uuid NOT NULL,
    kind           text NOT NULL,
    title          text NOT NULL,
    body           text,
    read_at        timestamptz,
    created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notifications_recipient
    ON activation.notifications (recipient_type, recipient_id, created_at DESC);

ALTER TABLE activation.youth
    ADD COLUMN IF NOT EXISTS bio text,
    ADD COLUMN IF NOT EXISTS public_profile boolean NOT NULL DEFAULT false;

ALTER TABLE activation.businesses
    ADD COLUMN IF NOT EXISTS email text,
    ADD COLUMN IF NOT EXISTS phone text,
    ADD COLUMN IF NOT EXISTS password_hash text;

CREATE UNIQUE INDEX IF NOT EXISTS businesses_email_ci_unique
    ON activation.businesses (lower(email)) WHERE email IS NOT NULL;

ALTER TABLE activation.opportunities
    ADD COLUMN IF NOT EXISTS approval_status text NOT NULL DEFAULT 'Approved'
        CHECK (approval_status IN ('Pending', 'Approved', 'Rejected')),
    ADD COLUMN IF NOT EXISTS created_by text NOT NULL DEFAULT 'staff';

CREATE INDEX IF NOT EXISTS idx_opportunities_approval ON activation.opportunities (approval_status);

-- Provider events that could not be matched to an open invoice (unknown
-- reference, already paid, over-payment). Money may have arrived: staff
-- must look at every one.
CREATE TABLE IF NOT EXISTS activation.unmatched_payments (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider          text NOT NULL,
    provider_ref      text NOT NULL,
    invoice_reference text,
    amount            numeric(12,2),
    method            text,
    reason            text NOT NULL,
    status            text NOT NULL DEFAULT 'Open' CHECK (status IN ('Open', 'Resolved')),
    resolution        text,
    created_at        timestamptz NOT NULL DEFAULT now(),
    resolved_at       timestamptz,
    UNIQUE (provider, provider_ref)
);

-- Access: the baseline's default privileges already deny anon/authenticated
-- on every new table in this schema, so no extra grants or policies are needed.

-- Defence in depth: the table that was missing RLS (not reachable by anon today).
ALTER TABLE IF EXISTS activation.rate_limit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE activation.unmatched_payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE activation.invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE activation.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE activation.payouts ENABLE ROW LEVEL SECURITY;
ALTER TABLE activation.payout_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE activation.notifications ENABLE ROW LEVEL SECURITY;
