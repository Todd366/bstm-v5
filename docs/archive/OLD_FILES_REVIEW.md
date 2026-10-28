# Review of the old prototype files

Originals are kept in `docs/archive/legacy/` as `.py.txt` (never imported, never deployed). `data/youth.json` (real names) was deleted.

| File | Why it was built that way | What v5 does instead | Ported |
|---|---|---|---|
| `bstm_activation.py` (v1, 338 lines) | First proof that the idea can run: a Termux menu that stores youth, businesses, trials and opportunities in JSON files and logs every event. | Same four things, now in Postgres with login, roles and an activity log. | Nothing left to port. |
| `bstm_activation_v2.py` | Added "thinking": keyword to department pathways for a youth, a business health audit that creates opportunities, capability records, a trial that completes into a score, matching, a knowledge-graph (nodes/edges), a cascade map (a Web job leads to Marketing, Analytics, Automation), ecosystem health. | Departments + brief (`brief_service`), field audits (`audit_service`), matching (`matching_service`), trials, progression. Graph and cascade not built. | Pathway idea already in `brief_service`. Cascade kept as roadmap item. |
| `bstm_activation_v3.py` | Deepened v2: weighted keyword lists per department, skill-gap analysis (skills a department needs minus skills owned), personalised trials, 10-area business audit routed to departments (e.g. Digital Presence -> Web Development), reputation formula, "100 trials" dashboard. | Intake scoring, diagnosis, audits with ratings, progression, verified vs declared skills. | **Skill gaps ported** (v5.5.1: "Skills to add next" on the youth home, from the live skill catalogue). Audit-area routing -> roadmap (structured job requirements). |
| `bstm_activation_v4.py` | A rewrite for safety: validated input (`ask_required`, `ask_number`), duplicate checks, integrity report. Never finished (no matching, trials). | Validation in `app/core/validation.py`, unique constraints, System tab. | Integrity idea -> System tab ledger check (already in). |
| `repair_bstm.py` | JSON files had drifted between versions (missing fields, broken links). It rebuilt each file to a standard shape. | Migrations plus database constraints make drift impossible. | None needed. |

## Lessons carried forward
- Every version added "intelligence" before "proof of money". v5 reversed that: evidence and ledger first.
- Keyword guessing (v2/v3) is weak for Setswana and small businesses; v5 uses structured choices. Keep that.
- Cascade idea (one finished job suggests the next job for the same business) is worth building after the first paying jobs exist.
