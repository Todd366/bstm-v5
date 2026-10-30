# Changelog

## 5.14.1
- Tests only: two staff pressing Confirm on the same payment, or Mark paid on the same payout, at the same instant on real Postgres. Exactly one succeeds, one payout is created, money is counted once. No behaviour change.

## 5.14.0
- Reports: CSV download for the month, and a Field agents section (people registered per agent, how many chose their own password).
- A test now guards the first-load size (budget 150 KB gzipped; currently about 33 KB).
- No database change.

## 5.13.0
- Agents can now support the people they registered: see their applications, see jobs that fit them, apply for them, and save proof of their work. Each action is logged as done by the agent. An agent can act only for people they registered; admins can act for any agent-registered person; self-signed people are never reachable this way (tested).
- No database change.

## 5.12.0
- **Field agents.** New staff role `agent`. An agent sees one tab, Register: full name, phone, village/town, optional goal, and a consent tick. The person is created with a one-time temporary password shown to the agent once; the agent never chooses the real password. The agent sees only the people they registered and whether each has chosen their own password. Admin, field and owner see everyone registered this way.
- Young people can change their own password (Profile). Agent-registered people are asked to choose their own on first login.
- Migration `20261030010000_field_agents.sql` (tap Update database). Agent role closed to every other staff route (tested).

## 5.11.0
- Young people can sign up and log in with a Botswana phone number instead of an email (71 234 567, 071234567 and +267 all work). One field: "Email or phone number". Staff reset codes work by phone number too. No SMS yet, so numbers are not verified; the password protects the account.
- Migration `20261030000000_youth_phone.sql` (tap Update database).

## 5.10.0
- Staff **Reports** tab (admin, finance): pick a month and see new people, new businesses, jobs posted, work submitted/approved, field cards, money received, paid to young people, where people joined from, and all-time totals. Copy-ready summary text. All counted from live records on Africa/Gaborone months.
- No database change.

## 5.9.1
- Trial form is now the full BSTM 100 Trials field card: identification, entry context, core questions, raw quotes, observation, exit snapshot (problem, insight, summary, interest, return, scores). Saves a draft on the phone while typing; checked on the server.
- Pattern tracker on My work (trial log, and after 10 trials the repeated problems and most-met business type). Business and staff see the card in full.
- No database change.

## 5.9.0
- Jobs can name the skills they need (up to 5). Matching uses them exactly: coverage, level, BSTM-verified, and area; explains what is still missing. Jobs without named skills still use text matching.
- Business "Post a job" has a skill picker; job cards show "Skills needed".
- Migration `20261029000000_job_requirements.sql` (apply via Update database).

## 5.8.0
- Owner can promote/demote team members (Team -> Change role); takes effect on their next request; logged.
- "Needs attention": the app checks itself (stuck payments/payouts/reviews, unpaid invoices, broken ledger facts, old records) and tells each role what is theirs. Greeting on the Queue.
- Support and finance staff no longer see a person's private questionnaire answers.
- Invariant tests: a full job-to-payout lifecycle must never trip a fail-level check.

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
