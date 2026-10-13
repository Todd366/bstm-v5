# BSTM Activation

Connects Batswana youth to real work: register → match → apply → trial → proof → progression.

- API: FastAPI + Postgres (Supabase, schema `activation`), deployed on Vercel.
- Frontend: `public/` (static, mobile-first, low-data, English/Setswana).
- Layers: `app/routes` (HTTP) → `app/api` (use-cases) → `app/services` (rules + SQL) · `app/core` (config, auth middleware, validation, logging).
- Auth: youth JWT for `/me/*`; admin `X-API-Key` for everything else non-public.
- Docs: `docs/AUDIT_2026-10-12.md` (findings + plan).

## Run
    pip install -r requirements.txt
    export BSTM_DATABASE_URL=... BSTM_JWT_SECRET=... BSTM_API_KEY=...
    uvicorn app.main:app --reload

## Test (safe: uses a temporary schema)
    BSTM_DATABASE_URL=... sh scripts/verify.sh

## Environment
`BSTM_DATABASE_URL` (session pooler, port 5432), `BSTM_JWT_SECRET`, `BSTM_API_KEY`, optional `BSTM_CORS_ORIGINS`, `BSTM_ENVIRONMENT=production`.
Apply new files in `migrations/` in order (they are additive and re-runnable).
