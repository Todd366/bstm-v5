-- Field agents: staff who register people on one phone, in villages and towns.
-- The person logs in with their phone number and a temporary password, and is
-- asked to choose their own. `registered_by` records who signed them up.
ALTER TABLE activation.staff DROP CONSTRAINT IF EXISTS staff_role_check;
ALTER TABLE activation.staff ADD CONSTRAINT staff_role_check
    CHECK (role IN ('admin', 'finance', 'field', 'support', 'agent'));
ALTER TABLE activation.youth ADD COLUMN IF NOT EXISTS registered_by text;
ALTER TABLE activation.youth ADD COLUMN IF NOT EXISTS must_change_password boolean NOT NULL DEFAULT false;
CREATE INDEX IF NOT EXISTS youth_registered_by_idx ON activation.youth (registered_by) WHERE registered_by IS NOT NULL;
