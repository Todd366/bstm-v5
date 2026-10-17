# Changelog

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
