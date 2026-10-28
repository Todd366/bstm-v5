# BSTM Activation: Roadmap and Working Rules

For anyone building this system (engineer, architect, Claude). Read this first. Updates go in this file, not in chat.

## Working rules (owner's standing instructions)
1. Owner communicates by copy-paste blocks only. No explanations in chat; all reasoning goes in this file or `docs/`.
2. Free tier only. Be precise, no negotiation, no filler.
3. Evidence over appearance (BSTM Production Signature): a thing is "done" only when a test, a browser check or a live measurement shows it. Record the evidence in `docs/HEALTH.md`.
4. Reuse before rebuilding. Before deleting or replacing anything, check what it knew and keep what is useful.
5. Layers: `routes` (HTTP) -> `api/service.py` (use-cases) -> `services` (rules + SQL). Money and approvals always record the actor.
6. Delivery: build in the sandbox, run `python3 shim pytest` + `tests/e2e/smoke.mjs`, commit, zip, send, give ONE Termux block. DB changes ship as a migration in `migrations/` applied by Staff -> Update database.

## Current state (v5.5.0, pushed as 3bf49b4)
Working and tested: register/login (youth, business, staff), matching, applications and offers, trials with evidence, approval -> job completion -> invoice -> payment -> payout, unmatched-payments inbox, staff roles, reset codes, invoice void, data export/delete, system check, in-app migrations, Setswana/English, offline shell.
Not done: see Phase 3-5.

## Phase 0: Verify what is live (do first, every release)
- [ ] /health shows the new version; Staff -> System shows no FAIL.
- [ ] Migrations applied (Update database). Check via Supabase: tables `staff`, `password_resets`, `invoices`, `field_audits`; skills count 41.
- [ ] First admin created under Team; shared key no longer used day to day.
- [ ] GitHub repo set to private (old history contains `data/` with names).

## Phase 1: Old-file review (done in v5.5.1)
Reviewed in `docs/archive/OLD_FILES_REVIEW.md`; originals in `docs/archive/legacy/`.
- [x] Skill gaps ported ("Skills to add next").
- [ ] Cascade: after a job completes, suggest the next job for that business (needs paying history first).
- [ ] Business audit area -> department routing, once job postings carry structured requirements.

## Phase 2: Bug hunt (continuous)
Method per module: read the code, write a failing test for each suspected bug, fix, keep the test.
Known suspects to test first:
- [ ] Concurrency: two staff confirm the same payment; business accepts while youth withdraws (locks exist; add concurrent tests on real Postgres).
- [ ] Support role can read youth `intake` (sensitive questionnaire) via `/youth/{id}`; restrict.
- [ ] Deleted youth: confirm they vanish from matching, lists, public profile, candidate lists.
- [ ] Invoice void then re-completion: confirm a replacement invoice is possible and idempotent.
- [ ] Rate-limit table growth: add scheduled cleanup of old `rate_limit_events`.
- [ ] Staff token lookup hits the DB on every staff request: measure; cache for a few seconds if slow.
- [ ] Time zones: all dates stored UTC, displayed in Africa/Gaborone.
- [ ] Money rounding and currency (BWP, 2 decimals) across split, payouts, reports.
- [ ] Error pages and offline behaviour on slow 2G connections; measure payload sizes (budget: first load under 150 KB).
- [ ] Accessibility: keyboard, labels, contrast, text size; test on a low-end Android.

## Phase 3: Wiring left (integration)
- [ ] Payment provider: owner's constraints are Absa savings card, DPO rejected. Candidate path: manual Orange Money / MyZaka confirm (live now) -> SMS-bridge adapter (built, needs a phone running the bridge) -> a gateway adapter once a provider accepts the business. Decision needed from owner; see project doc `payments-botswana-2026-10`.
- [ ] Notifications beyond in-app: SMS or WhatsApp (provider decision), keep in-app as source of truth.
- [ ] Phone-number login / OTP (needs SMS provider).
- [ ] Structured job requirements (department + skills on a posting) so matching stops guessing.
- [ ] Field audit -> suggested jobs -> business confirmation loop (reuse existing audit and diagnosis services).
- [ ] Reports: monthly numbers for BSTM (people helped, jobs, money moved, verified skills) from live data.
- [ ] Public verification: shareable proof page for a youth's verified work (opt-in, exists as public profile; extend with evidence).

## Phase 4: Production hardening
- [ ] Separate Supabase project (activation is sharing "bstm-marketplace-app"); transaction pooler for serverless.
- [ ] Backups: Supabase backups + a monthly export test restore.
- [ ] Monitoring: Vercel runtime error check weekly; alert on System tab FAIL.
- [ ] Legal: confirm holding client money, terms of use, privacy notice, data-protection registration for Botswana; CIPA business registration (owner action).
- [ ] Load test on realistic numbers (100 concurrent users) and fix the slowest queries.
- [ ] Security review: dependency pinning, CSP, secrets rotation, staff password policy.

## Phase 5: Reach (villages, towns, cities)
- [ ] Agent mode: a field agent registers and supports people on one phone (BSTM agents/specialists recruitment flow).
- [ ] Low-data mode: no images, small JSON, resumable submissions.
- [ ] Setswana review by a native speaker for every screen.
- [ ] Pilot in one town; record evidence; adjust.

## Definition of done for any task
Code + test + browser check where UI changed + `docs/HEALTH.md` line + changelog line + the Termux block.
