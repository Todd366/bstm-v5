-- Migration: rate_limit_events
--
-- Backs real rate limiting for POST /youth and POST /businesses, both
-- of which are intentionally public (no API key) since they're
-- self-registration endpoints for anonymous members of the public.
-- That openness was a known, explicitly flagged gap: without this,
-- either endpoint can be spammed with zero friction.
--
-- A stateless Vercel deployment can't do in-memory rate limiting
-- reliably (no shared state between invocations), so this uses
-- Postgres directly rather than adding a new piece of infrastructure
-- (e.g. Redis) for a single early-stage feature.
--
-- Rows are cleaned up opportunistically inline (see
-- rate_limit_service.py) rather than via a cron job, to avoid needing
-- separate scheduled-task infrastructure at this scale.

CREATE TABLE IF NOT EXISTS activation.rate_limit_events (
    id         bigserial PRIMARY KEY,
    ip         text NOT NULL,
    endpoint   text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rate_limit_events_lookup
    ON activation.rate_limit_events (ip, endpoint, created_at);
