-- Migration: enable row level security on activation.field_audits (re-runnable).
-- The app connects as the table owner, so access through the API is unchanged;
-- this only closes direct access through Supabase's public data API.
ALTER TABLE activation.field_audits ENABLE ROW LEVEL SECURITY;
