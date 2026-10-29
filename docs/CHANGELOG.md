# Changelog

## 5.7.0
- Owner is built in (no account to create): sign in at Staff sign in with bstm366@gmail.com and the owner password (`BSTM_OWNER_PASSWORD`, or the staff key if not set).
- Staff sign-in has "Create a staff account": the request waits (switched off) until the owner approves it and picks a role.
- Owner can delete any staff account; the owner email is reserved.
- Migration `20261028000000_staff_signup.sql` (apply via Update database).

## 5.6.0
- Owner role (BSTM_OWNER_EMAIL, default bstm366@gmail.com): edit and delete any person, business or job; money records protected; every change logged.
- Team management is owner-only. Test-data review list in Staff -> Owner.
- Fixes: tab bar overflow on phones, deleted members still counted.
- `docs/AUDIT_2026-10-28.md`.

## 5.5.2
- Emergency admin key can be set as `BSTM_STAFF_KEY` (falls back to `BSTM_API_KEY`).

## 5.5.1
- Youth home shows "Skills to add next" (ported from the old v3 skill-gap analysis).
- Old prototype files archived with a review (`docs/archive/OLD_FILES_REVIEW.md`).
- `docs/ROADMAP.md` added.

## 5.5.0
- Staff accounts with roles (admin, finance, field, support); shared key kept as emergency admin.
- Money and approval actions record who did them.
- Staff-issued password reset codes for youth and businesses ("Forgot password?").
- Cancel (void) an unpaid invoice.
- Members can download their data and delete their account.
- System check (Staff -> System) measures setup and ledger health.
- Removed old prototype files (`bstm_activation*.py`, `repair_bstm.py`, `data/`).
- Migration `20261021000000_staff_resets_privacy.sql` (apply via Staff -> Update database).

## v5.4.0 — 2026-10-17
**Money loop and every role's screens.** Evidence labels: backend VERIFIED by 120 tests on PG16; frontend VERIFIED by a real-Chromium smoke test against a mocked API (tests/e2e/smoke.mjs); FastAPI route layer and production behaviour UNASSESSED (never run).
- Approved work completes the job and issues the invoice in one transaction (`complete_trial`). A job can no longer be completed or invoiced without approved work.
- `youth.revenue` now means money actually paid out (was: counted at completion).
- Businesses: accounts (email + password), login, post jobs (staff approve), choose applicants, approve work, pay invoices (Idempotency-Key), alerts.
- Staff: queue now shows jobs to approve, payments to confirm, payouts to send, unmatched money; Money tab (invoices, record cash/EFT).
- Unmatched provider money (unknown invoice, already paid, over-payment) is parked for staff, never dropped.
- Youth: Money (earnings, payout account), profile + opt-in public profile page (`#/p/<id>`), alerts bell, job search/filter/paging, stop work, cancelled trial can be restarted, submitted link becomes trial evidence.
- Fixes: duplicate rows from multiple trials per assignment, CORS PUT, version string, RLS on all new tables and `rate_limit_events`, stale files removed (`.cleanup_backup`).
- Config: `BSTM_PAY_INSTRUCTIONS` (shown on invoices), `BSTM_WEBHOOK_SECRET_<PROVIDER>`.

## Not done (see docs/REALITY_AUDIT_2026-10-17.md)
Phone/OTP login, password reset, SMS/WhatsApp notifications, staff accounts with roles, deposit-before-start, invoice void/dispute, separate Supabase project, CI that runs the FastAPI routes.

## v5.4.1
- In-app database updater: staff console shows "Database update needed" after sign-in and applies bundled migrations with one tap (`GET /admin/migrations`, `POST /admin/migrations/apply`, tracked in `schema_migrations`). No SQL editor required.
