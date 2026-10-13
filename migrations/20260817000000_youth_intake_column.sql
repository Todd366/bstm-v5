-- Migration: youth_intake_column
--
-- The real frontend (index.html/style.css/script.js — the "Threshold"
-- onboarding flow) collects a 10-step discovery questionnaire: identity,
-- life position, education, interests, skills, resources, financial
-- reality, availability, obstacles, aspiration. That's richer than the
-- youth table's existing columns (name/location/passion/goal/
-- availability/equipment) support.
--
-- Rather than adding a dozen narrow columns for data no service logic
-- acts on yet, this stores the full questionnaire response as JSONB.
-- If/when a specific field (e.g. financial_reality) needs real query
-- logic or its own progression rules, promote it to a real column then
-- — this is deliberately a holding area, not a permanent design.

ALTER TABLE activation.youth
    ADD COLUMN IF NOT EXISTS intake jsonb;
