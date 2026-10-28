# Health of BSTM Activation (v5.5.0)

Each line says how it is known. "Tested" = automated test passes in CI. "Measured live" = shown on the staff System tab. "Not done" = real gap.

| Area | State | Evidence |
|---|---|---|
| Job → work → approval → invoice → payment → payout | Working | Tested (ledger flow tests) |
| Business hiring, approval of work, invoices | Working | Tested + browser test |
| Staff roles, individual logins, void invoice | Working | Tested (role matrix over the real middleware) |
| Password reset (staff-issued code) | Working | Tested |
| Data export / account deletion | Working | Tested |
| Live checks (env, secrets, ledger balance, stuck money) | Working | Measured live (System tab) |
| Automatic payment collection (card/mobile money) | Not done | Needs a provider decision; payments are recorded by hand |
| SMS / WhatsApp alerts | Not done | In-app alerts only |
| Phone-number login / OTP | Not done | Email + password only |
| Separate database from other apps, backups schedule | Not done | Shares a Supabase project; use Supabase backups |
| Deposit before work starts | Not done | Business-model decision |
| Real users at scale | Unproven | No load test run |

Update this file only with things that were actually checked.
