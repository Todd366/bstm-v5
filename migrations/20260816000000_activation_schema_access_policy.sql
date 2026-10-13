-- Migration: activation_schema_access_policy
--
-- CONTEXT: Supabase's security linter flags every activation.* table as
-- "RLS enabled, no policy". Verified this is NOT an active vulnerability:
--   - Zero GRANTs exist to anon/authenticated/public on any activation table
--   - Neither anon nor authenticated even have USAGE on the activation
--     schema itself (has_schema_privilege returns false for both)
--   - RLS enabled + zero policies defaults to deny-all for any role that
--     isn't the table owner / doesn't bypass RLS (bstm_v5's backend
--     connects as the `postgres` role, which does bypass RLS)
--
-- bstm_v5 has no end-user-facing Supabase client usage — every request
-- goes through the FastAPI backend (app/main.py), authenticated via its
-- own API key middleware, using the postgres role. There is currently no
-- legitimate reason for anon/authenticated to touch this schema at all.
--
-- This migration doesn't change runtime behavior (everything below is
-- already true) — it makes the locked-down posture EXPLICIT and
-- version-controlled, so a future person doesn't see the linter warning,
-- assume it's an oversight, and loosen access without understanding why
-- it was denied. If bstm_v5 ever adds direct client-side Supabase access
-- (e.g. a mobile app reading its own youth profile via anon/authenticated
-- with a real Supabase Auth session), real RLS policies scoped to that
-- use case should be written then — not a blanket allow.

REVOKE ALL ON ALL TABLES IN SCHEMA activation FROM anon, authenticated, public;
REVOKE ALL ON SCHEMA activation FROM anon, authenticated, public;

-- Also cover any tables added after this migration runs, so this
-- protection doesn't silently lapse for new tables in the schema.
ALTER DEFAULT PRIVILEGES IN SCHEMA activation
    REVOKE ALL ON TABLES FROM anon, authenticated, public;
