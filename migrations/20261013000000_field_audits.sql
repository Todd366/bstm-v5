-- Migration: field_audits. Additive, re-runnable, `activation` schema only.
CREATE TABLE IF NOT EXISTS activation.field_audits (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id   uuid REFERENCES activation.businesses(id) ON DELETE SET NULL,
    business_name text NOT NULL,
    location      text NOT NULL,
    ratings       jsonb NOT NULL DEFAULT '{}'::jsonb,
    rooms         integer[] NOT NULL DEFAULT '{}',
    insight       text,
    score         integer NOT NULL CHECK (score BETWEEN 1 AND 10),
    auditor       text NOT NULL DEFAULT 'staff',
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_field_audits_created ON activation.field_audits (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_field_audits_business ON activation.field_audits (business_id);
