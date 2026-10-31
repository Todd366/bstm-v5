-- Shop owners can log in with a phone number. Only clean +267 numbers are
-- made unique, so older free-text values are left alone.
CREATE UNIQUE INDEX IF NOT EXISTS businesses_phone_unique
    ON activation.businesses (phone)
    WHERE phone ~ '^\+267[3-7][0-9]{7}$';
