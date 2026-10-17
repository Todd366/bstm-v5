# BSTM Activation: operations runbook

## Flow
Youth register (questionnaire → brief) → business registers (diagnosis) → staff post jobs → youth apply or staff offer →
staff accept → youth start work → submit → staff review + score → complete → staff mark job complete (youth revenue share booked).
Everything is logged to `activity` (Staff → Queue → Recent activity).

## Deploy
Push to `master` → Vercel builds. Env: `BSTM_DATABASE_URL` (Supabase session pooler :5432), `BSTM_JWT_SECRET`, `BSTM_API_KEY`, `BSTM_ENVIRONMENT=production`, optional `BSTM_CORS_ORIGINS`.
Migrations: run new `migrations/*.sql` in order in the Supabase SQL Editor (additive, re-runnable).

## Health
`GET /health` → 200 ok / 503 database down. With header `X-API-Key` the 503 body includes the error text.
Logs are JSON, each with `request_id`; users see the id on errors.

## Rotate secrets
Change `BSTM_API_KEY` in Vercel and redeploy (staff re-enter key). Changing `BSTM_JWT_SECRET` logs everyone out.

## Tests
`BSTM_DATABASE_URL=... sh scripts/verify.sh` (temporary schema, real data untouched).

## v5.4 additions
- Env: `BSTM_ENVIRONMENT=production` (closes CORS), `BSTM_PAY_INSTRUCTIONS` (text shown to businesses: where to send money), `BSTM_WEBHOOK_SECRET_SMS_BRIDGE` / `_GATEWAY` (only if you connect an automation).
- Money runbook: business submits payment reference → Queue "Payments to confirm": confirm only after the money is visible in the account → payout appears in "Payouts to send": send from MyZaka/bank, paste the receipt reference, "Mark as paid". Unmatched money: resolve with a note (refund or hand-match).
- Browser smoke test: `NODE_PATH=<playwright> node tests/e2e/smoke.mjs`.
