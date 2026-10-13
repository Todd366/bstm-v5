-- Migration: youth_authentication
--
-- Adds real login capability to youth. Until now, POST /youth created
-- an anonymous, one-time registration with no way for that person to
-- come back and prove it's them — meaning nothing past the intake
-- questionnaire in the product vision (trials, capability profile,
-- opportunities, dashboard, everything) was actually reachable,
-- regardless of how solid the backend behind those features was.
--
-- email is UNIQUE but nullable: the 14 existing youth records created
-- during tonight's testing never collected an email, and backfilling
-- fake ones would be worse than leaving them null. New registrations
-- require it (enforced in the service layer, not a NOT NULL
-- constraint, so existing rows aren't broken by this migration).
--
-- password_hash stores a PBKDF2-HMAC-SHA256 hash (stdlib hashlib, no
-- new C-extension dependency — bcrypt/argon2 were deliberately
-- avoided given how much trouble this project has already had with
-- packages that don't compile cleanly on Termux/Vercel).

ALTER TABLE activation.youth
    ADD COLUMN IF NOT EXISTS email text,
    ADD COLUMN IF NOT EXISTS password_hash text;

CREATE UNIQUE INDEX IF NOT EXISTS youth_email_ci_unique
    ON activation.youth (lower(email))
    WHERE email IS NOT NULL;
