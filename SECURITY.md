# Security

- Report problems privately to the BSTM team; do not open public issues containing data.
- Secrets live only in the host's environment settings (see `.env.example`). Never commit them.
- The owner is built in (no database row): signs in with the owner email + owner password (env). Staff accounts are requested by sign-up and approved by the owner.
- Access: youth and business accounts use their own login tokens. Staff use individual accounts with roles (admin, finance, field, support); the shared `BSTM_API_KEY` is emergency-only and always acts as admin.
- Every money or approval action records who did it (Activity log).
- Passwords: PBKDF2-SHA256, 600k rounds. Logins and resets are rate limited. Reset codes are one-time, expire in 24h, lock after 5 wrong tries.
- Personal data: members can download their data and delete their account (`/me/export`, `/me/delete`).
- Database: Row Level Security is on for all `activation` tables; the app connects with a server-side role only.
