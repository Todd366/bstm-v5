-- Young people can sign up and log in with a phone number (many have no email).
-- Stored as +267XXXXXXXX. Unique per person; email stays optional.
ALTER TABLE activation.youth ADD COLUMN IF NOT EXISTS phone text;
CREATE UNIQUE INDEX IF NOT EXISTS youth_phone_unique
    ON activation.youth (phone)
    WHERE phone IS NOT NULL;
