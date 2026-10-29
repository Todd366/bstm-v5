"""Who may call which staff (admin-tier) route.

The shared BSTM_API_KEY always acts as `admin` (break-glass). Staff accounts
carry one role. Anything not listed here is admin-only, so a new route is
closed by default."""

ALL = {"admin", "finance", "field", "support"}
MONEY = {"admin", "finance"}
FIELD = {"admin", "field"}
PEOPLE_READ = {"admin", "field", "support"}

# (path prefix, method or None for any, allowed roles) — first match wins.
RULES = [
    ("/admin/staff", None, {"owner"}),
    ("/admin/owner", None, {"owner"}),
    ("/admin/me", None, ALL),
    ("/admin/attention", None, ALL),
    ("/admin/queue", None, ALL),
    ("/admin/stats", None, ALL),
    ("/admin/activity", None, ALL),
    ("/admin/resets", None, {"admin", "support"}),
    ("/invoices", None, MONEY),
    ("/payments", None, MONEY),
    ("/payouts", None, MONEY),
    ("/unmatched-payments", None, MONEY),
    ("/youth", "GET", PEOPLE_READ),
    ("/businesses", "GET", PEOPLE_READ),
    ("/opportunities", None, FIELD),
    ("/assignments", None, FIELD),
    ("/trials", None, FIELD),
    ("/youth", None, FIELD),
    ("/youth-capabilities", None, FIELD),
    ("/businesses", None, FIELD),
    ("/capabilities", None, FIELD),
    ("/audits", None, FIELD),
    ("/evidence", None, FIELD),
    ("/matches", None, FIELD),
]


def is_allowed(role, method, path):
    """The owner may do anything; everyone else is limited by RULES."""

    return role == "owner" or role in allowed_roles(method, path)


def allowed_roles(method, path):
    for prefix, rule_method, roles in RULES:
        if (path == prefix or path.startswith(prefix + "/")) and rule_method in (None, method):
            return roles

    return {"admin"}
