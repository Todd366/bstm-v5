-- Migration: staff can ask for an account; it stays off until the owner approves it.
-- Additive and re-runnable. `activation` only.
ALTER TABLE activation.staff ADD COLUMN IF NOT EXISTS approved boolean NOT NULL DEFAULT true;
