"""Rule-based first diagnosis of a business from its stated problem.
It SUGGESTS opportunities; staff review them before anything is posted."""

import re

from app.core.validation import require_uuid
from app.db.database import transaction

RULES = [
    (r"website|online|digital|internet|facebook|whatsapp|app\b",
     "No usable digital presence", "Web Development",
     "Build a simple website or WhatsApp catalogue for the business."),
    (r"money|account|financ|book ?keep|record|profit|cash|debt|loan",
     "No structured financial tracking", "Finance & Accounting",
     "Set up simple bookkeeping and monthly money reports."),
    (r"customer|market|sales|advert|promot|brand|sell",
     "Weak customer acquisition", "Digital Marketing & Advertising",
     "Run a small campaign to reach new local customers."),
    (r"deliver|logistic|transport|stock|supply|route",
     "Delivery and logistics gap", "CabLink Transportation",
     "Organise reliable delivery or transport for orders."),
    (r"staff|worker|hire|employee|train|skills",
     "Staffing and skills gap", "Human Resources & Talent Development",
     "Recruit and train help for the business."),
    (r"farm|crop|water|irrigat|livestock|chicken|poultry|garden",
     "Farm productivity gap", "Micro Farming & Urban Agriculture",
     "Run a documented pilot to improve yield and reduce costs."),
    (r"design|logo|packag|poster|flyer",
     "Weak branding", "Graphic Design & Branding",
     "Create a logo, flyer and brand kit."),
]


def diagnose(main_problem, business_name=""):
    text = (main_problem or "").lower()
    findings = []

    for pattern, title, department, task in RULES:
        if re.search(pattern, text):
            findings.append(
                {
                    "title": title,
                    "department": department,
                    "opportunity": {
                        "title": task.split(".")[0] + " - " + business_name if business_name else task.split(".")[0],
                        "description": task + " Problem stated by the owner: " + (main_problem or "")[:300],
                        "department": department,
                    },
                }
            )

    if not findings:
        findings.append(
            {
                "title": "General operations review",
                "department": "Research & Development",
                "opportunity": {
                    "title": "Operations review - " + business_name if business_name else "Operations review",
                    "description": "Visit the business, observe operations and report findings. Problem stated: " + (main_problem or "")[:300],
                    "department": "Research & Development",
                },
            }
        )

    return findings


def diagnose_business(business_id):
    business_id = require_uuid(business_id, "Business")

    with transaction() as db:
        row = db.execute(
            "SELECT name, main_problem FROM businesses WHERE id = ?", (business_id,)
        ).fetchone()

    if not row:
        raise ValueError("Business not found")

    return diagnose(row["main_problem"], row["name"])
