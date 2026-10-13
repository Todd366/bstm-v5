-- Migration: baseline_activation_schema
--
-- This is a SNAPSHOT of the activation schema's actual current state in
-- Supabase (project bstm-marketplace-app / tvtfxkavjqvurdezhyvu), captured
-- directly from information_schema/pg_catalog on 2026-08-15. It did not
-- previously exist as a file in this repo — the schema only lived in
-- Supabase's own migration history (activation_core_schema,
-- enforce_unique_names, fix_trial_status_vocabulary), which this repo
-- had no local copy of. This file makes the schema reproducible from
-- version control.
--
-- NOTE: this Supabase project is shared with an unrelated marketplace
-- app living in the `public` schema (orders, delivery, profiles, rooms,
-- etc.). This migration only touches the `activation` schema, which is
-- exclusively bstm_v5's.
--
-- `evidence` exists in the schema but is not yet used by any service in
-- app/services/ — it appears to be scaffolding for the trial-evidence
-- concept described in the product vision doc, not yet wired up.

CREATE SCHEMA IF NOT EXISTS activation;

-- ── youth ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS activation.youth (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name                    text NOT NULL,
    location                text NOT NULL,
    passion                 text,
    goal                    text NOT NULL,
    availability            text,
    equipment               text,
    level                   text NOT NULL DEFAULT 'Explorer',
    capability_score        numeric NOT NULL DEFAULT 0,
    learning_score          numeric NOT NULL DEFAULT 0,
    reputation_score        numeric NOT NULL DEFAULT 50,
    reliability_score       numeric NOT NULL DEFAULT 50,
    completed_trials        integer NOT NULL DEFAULT 0,
    completed_opportunities integer NOT NULL DEFAULT 0,
    revenue                 numeric NOT NULL DEFAULT 0,
    created_at              timestamptz NOT NULL DEFAULT now(),
    updated_at              timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS youth_name_ci_unique
    ON activation.youth (lower(name));

-- ── businesses ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS activation.businesses (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name                    text NOT NULL,
    owner                   text NOT NULL,
    sector                  text NOT NULL,
    location                text NOT NULL,
    main_problem            text,
    audit_status            text NOT NULL DEFAULT 'Pending'
        CHECK (audit_status = ANY (ARRAY['Pending', 'InProgress', 'Completed'])),
    opportunities_generated integer NOT NULL DEFAULT 0,
    created_at              timestamptz NOT NULL DEFAULT now(),
    updated_at              timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS businesses_name_ci_unique
    ON activation.businesses (lower(name));

-- ── capabilities ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS activation.capabilities (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text NOT NULL UNIQUE,
    category    text NOT NULL,
    description text,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- ── opportunities ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS activation.opportunities (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id uuid REFERENCES activation.businesses(id),
    department  text,
    title       text NOT NULL,
    description text,
    budget      numeric NOT NULL DEFAULT 0,
    status      text NOT NULL DEFAULT 'Open'
        CHECK (status = ANY (ARRAY['Open', 'Matched', 'Assigned', 'InProgress', 'Completed', 'Cancelled'])),
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_opportunities_business
    ON activation.opportunities (business_id);

-- ── opportunity_matches ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS activation.opportunity_matches (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    youth_id       uuid NOT NULL REFERENCES activation.youth(id),
    opportunity_id uuid NOT NULL REFERENCES activation.opportunities(id),
    match_score    numeric NOT NULL DEFAULT 0,
    reason         jsonb,
    status         text NOT NULL DEFAULT 'Suggested'
        CHECK (status = ANY (ARRAY['Suggested', 'Accepted', 'Rejected', 'Expired'])),
    created_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (youth_id, opportunity_id)
);

CREATE INDEX IF NOT EXISTS idx_matches_youth
    ON activation.opportunity_matches (youth_id);
CREATE INDEX IF NOT EXISTS idx_matches_opportunity
    ON activation.opportunity_matches (opportunity_id);

-- ── opportunity_assignments ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS activation.opportunity_assignments (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    youth_id       uuid NOT NULL REFERENCES activation.youth(id),
    opportunity_id uuid NOT NULL REFERENCES activation.opportunities(id),
    match_id       uuid REFERENCES activation.opportunity_matches(id),
    status         text NOT NULL DEFAULT 'Pending'
        CHECK (status = ANY (ARRAY['Pending', 'Accepted', 'Declined', 'Completed', 'Cancelled'])),
    assigned_at    timestamptz NOT NULL DEFAULT now(),
    accepted_at    timestamptz,
    completed_at   timestamptz,
    created_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (youth_id, opportunity_id)
);

CREATE INDEX IF NOT EXISTS idx_assignments_youth
    ON activation.opportunity_assignments (youth_id);

-- ── trials ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS activation.trials (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id       uuid NOT NULL REFERENCES activation.opportunity_assignments(id),
    title               text,
    description         text,
    status              text NOT NULL DEFAULT 'Created'
        CHECK (status = ANY (ARRAY['Created', 'Active', 'Submitted', 'Under Review', 'Completed', 'Cancelled'])),
    submission          jsonb,
    review              jsonb,
    cancellation_reason text,
    started_at          timestamptz,
    submitted_at        timestamptz,
    reviewed_at         timestamptz,
    completed_at        timestamptz,
    cancelled_at        timestamptz,
    created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_trials_assignment
    ON activation.trials (assignment_id);

-- ── evidence (schema exists; not yet used by app/services/) ───────────
CREATE TABLE IF NOT EXISTS activation.evidence (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    youth_id      uuid NOT NULL REFERENCES activation.youth(id),
    trial_id      uuid REFERENCES activation.trials(id),
    capability_id uuid REFERENCES activation.capabilities(id),
    kind          text NOT NULL
        CHECK (kind = ANY (ARRAY['Portfolio', 'Screenshot', 'Document', 'BusinessApproval', 'Assessment', 'Transaction', 'Other'])),
    url           text,
    notes         text,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_evidence_youth
    ON activation.evidence (youth_id);

-- ── youth_capabilities ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS activation.youth_capabilities (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    youth_id      uuid NOT NULL REFERENCES activation.youth(id),
    capability_id uuid NOT NULL REFERENCES activation.capabilities(id),
    level         text NOT NULL DEFAULT 'Beginner'
        CHECK (level = ANY (ARRAY['Beginner', 'Developing', 'Intermediate', 'Advanced', 'Expert'])),
    verified      boolean NOT NULL DEFAULT false,
    created_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (youth_id, capability_id)
);

CREATE INDEX IF NOT EXISTS idx_youth_capabilities_youth
    ON activation.youth_capabilities (youth_id);

-- ── activity (audit log, no FKs by design) ─────────────────────────────
CREATE TABLE IF NOT EXISTS activation.activity (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event      text NOT NULL,
    actor_id   uuid,
    target_id  uuid,
    details    jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_activity_created
    ON activation.activity (created_at DESC);
