# Reality audit — BSTM Activation v5.4 (2026-10-17)

Evidence labels: **VERIFIED** (observed live or in code/tests) · **CODE-READ** (read, not executed end-to-end) · **UNASSESSED**.

## 0. What is true right now
| Fact | Label |
|---|---|
| Production runs v5.3 (commit 9a8c1fe). v5.4 (ledger, business portal, notifications) is **not deployed**. `/health` 200, DB ok. | VERIFIED |
| Production reports `environment=development` → CORS `*`; version string says 5.1.0. | VERIFIED |
| Live DB lacks migrations 20261012 and 20261013: **1 skill in catalogue (not 41)**, no `field_audits` table → staff "Field audit" screen errors. | VERIFIED |
| Live DB has no ledger tables, no `bio/public_profile` columns (v5.4 not applied). | VERIFIED |
| Live data: 21 youth, 3 businesses, 4 jobs, 4 assignments, 2 trials, 0 invoices. | VERIFIED |
| anon/authenticated have no USAGE on schema `activation` → `rate_limit_events` RLS-off is not exploitable today; enable RLS anyway. | VERIFIED |
| Same Supabase project hosts an unrelated marketplace/wallet (THB, rooms, stripe fdw, `payments_layer_v1` today). Shared blast radius and pooler slots. | VERIFIED |
| 113 service/middleware tests pass on local PG16. FastAPI routes and the whole frontend have **never been executed** (no pip access). | VERIFIED |

## 1. Architecture questioned against reality
1. **Staff are the bottleneck on every step**: accept applicant, review work, complete job, confirm payment, pay out, approve job. One person = the platform's ceiling. Businesses (who know whether work was done) have no say. → Delegate: business accepts applicants and confirms completion on its own jobs; staff only audit.
2. **Single shared admin key**: no per-staff identity, no rotation, `confirmed_by="staff"` for money. Violates RBAC/audit gates. → staff accounts with roles (admin, finance, field agent).
3. **Pay-after model puts all risk on the youth**: work → complete → invoice → business pays (maybe). No deposit, no dispute, no void/refund function (`Void` status exists, nothing sets it). → deposit-before-start (≥30–50%), void/dispute path.
4. **BSTM holds client money then pays youth** (70/30) = escrow/money-handling. Check Botswana payment-services/NBFIRA rules before scale. (Legal question, not code.) UNASSESSED.
5. **Email-only identity.** Many youth in villages have a phone, not email. No password reset, no email/phone verification anywhere → a forgotten password = lost account and lost earnings history. → phone number + SMS/WhatsApp OTP login, reset flow.
6. **Notifications exist only in-app.** An offer or payout reaches nobody who isn't already in the app on data. → SMS/WhatsApp outbound adapter (same adapter pattern as payments).
7. **Serverless + session pooler**: one DB connection per request on Supabase session-mode pooler (small client-slot limit, shared with the marketplace). Concurrency spike = "max clients" errors. → transaction pooler (6543) or a pool-per-instance with small cap; separate Supabase project for Activation.
8. **Matching is English keyword matching** of skill names in job text. Setswana or plain-language jobs match nobody; with 1 live skill it matches almost nothing. → fix catalogue (apply migration), add department/skill picker on job posting so matching uses structured data, not prose.
9. **Static admin key in `sessionStorage`, JWT 14 days, no revocation.** Acceptable for pilot; not for money.
10. **No backups/restore drill, no alerting, no error tracking.** UNASSESSED beyond Vercel logs.

## 2. Logic bugs and lifecycle gaps (by role)
**Youth**
- B1 `youth.revenue` ("Earned" on Home) is increased at job completion, before any money arrives; contradicts the ledger. Fix: show ledger totals (earned/pending/paid) only. CODE-READ.
- B2 Proof never attaches to a trial: UI posts evidence without `trial_id`, so staff review screen ("Proof: …") is always empty. CODE-READ.
- B3 Trial cancel has no UI; a cancelled trial leaves assignment Accepted and hides "Start work" (trial exists) → permanently stuck if staff cancels via API. CODE-READ.
- B4 No screens for: profile edit, public profile, earnings, payout account, notifications. Backend exists (v5.4).
- B5 Passwords can't be changed or reset.

**Business**
- B6 Whole `/biz` portal and `/businesses/login` have **no UI**; the registration form has no email/password, so no business can ever get an account.
- B7 Business cannot choose among applicants, cannot mark work done.
- B8 Email never verified; anyone can register any business name (jobs are approval-gated, accounts are not).

**Staff**
- B9 `complete_assignment` does not require the trial to be Completed → job can be invoiced with no proof ("evidence over appearance" violated). Trial approval and assignment completion are two separate manual steps on two screens → approved work can sit un-invoiced forever. Fix: completing a trial approval triggers assignment completion (or one combined action).
- B10 Queue UI lacks the v5.4 sections (pending jobs, payments, payouts); no ledger/invoice screen; no pagination/search on youth/businesses (hard cap 200).
- B11 Webhook for an invoice that is already Paid / over-paid returns 409 forever; the money received is recorded nowhere. Need an "unmatched payments" inbox.
- B12 Two simultaneous identical webhooks can both pass the idempotency pre-check; second gets 409 (safe, but noisy). Low.
- B13 SMS-forward bridge is spoofable (sender IDs can be forged); auto-confirm should require amount+reference match and staff spot check until a real gateway exists.

**Ops/config**
- B14 `APP_VERSION` default "5.1.0" and `pyproject` 5.1.0 stale. B15 `BSTM_ENVIRONMENT` unset → CORS `*`. B16 CORS `allow_methods` lacks PUT (only matters cross-origin). B17 `.cleanup_backup/` (old models, `.broken_import_backup`) sits in the repo dir (git-ignored, but shipped in the zip). B18 `sw.js` cache name still v5.2.

## 3. Route map vs UI (all verified from source)
- Public 15 routes: UI covers register/login youth, register business, catalogue. **No UI**: `/businesses/login`, `/public/profiles/{id}`, `/webhooks/{p}` (machine).
- `/me` 25 routes: UI covers 14. **No UI**: profile PUT, payout-account GET/PUT, earnings, notifications GET/read, trial cancel, `/me/trials`, `/me/trials/{id}`, browse filters.
- `/biz` 8 routes: **0 UI**.
- Admin 52 routes: UI covers ~24. **No UI**: approval, invoices, payments confirm/reject, payouts paid/fail, `/matches`, `/youth/{id}/matches|discover|assignments|trials`, `/assignments/{id}`, `/trials/{id}` GET/cancel/start, `/assignments/{id}/trials`.
Rule: a route with no UI and no machine caller is dead weight or an unfinished feature.

## 4. Unused / archived code and how to use it
| Item | Verdict |
|---|---|
| `.cleanup_backup/models/*`, `database.py`, `trial_service.py.*` | Pre-Postgres dead code. **Delete** (record in git history). |
| `docs/BSTM_V5_ARCHITECTURE_AUDIT_20260802…txt` | Stale; archive under `docs/archive/`. |
| `department_catalog.py` + `departments.py` + `brief_service` + `diagnosis_service` | Live; feed registration brief and business diagnosis. Extend: show department on job post, use for matching. |
| Admin routes `/youth/{id}/matches`, `/discover`, `/matches` POST, `/assignments/{id}/trials`, `/trials/{id}/start|cancel` | Built, unused by UI → expose in a per-youth staff detail page (matches, history, trials). |
| `system_health()` (counts) | Used by `/admin/stats`; extend into the Signature health scorecard. |
| `scripts/diagnose_connection.py` | Keep (ops). |
| Ledger/notifications/profiles/business portal (v5.4) | Finished backend, needs frontend (next build). |

## 5. Fix order (what survives reality first)
1. **Apply migrations** 20261012 → 20261013 → 20261016 in Supabase; deploy v5.4; set `BSTM_ENVIRONMENT=production`.
2. **Close lifecycle loops**: trial approval → assignment completion; business accepts applicants/confirms completion; revenue field replaced by ledger totals; evidence attached to trial.
3. **Frontend for v5.4** (earnings, payout account, notifications, profile, business portal, staff money screens) — otherwise the money loop is unusable.
4. **Phone + OTP identity, password reset, SMS/WhatsApp notifications** (adapter pattern).
5. **Staff accounts with roles**; per-action audit identity.
6. **Deposit-before-start**, void/dispute, unmatched-payments inbox.
7. **Own Supabase project** + transaction pooler; backups; error alerts.
8. Execute the route layer in CI (install FastAPI in the GitHub Action; `TestClient` role matrix) — currently only reasoned, never run.
