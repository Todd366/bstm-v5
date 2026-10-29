"""The BSTM 100 Trials field card (card + exit snapshot), checked on the server.

One business = one core problem. The card keeps what was heard (quotes) apart
from what was seen (observation) and what it means (insight)."""

from datetime import date

CHOICES = {
    "btype": ("retail", "salon", "food", "services", "other"),
    "size": ("S", "M", "L"),
    "entry_type": ("walk-in", "invited", "waited", "redirected"),
    "reaction": ("friendly", "neutral", "defensive", "busy"),
    "environment": ("busy", "calm", "chaotic"),
    "interest": ("yes", "no", "neutral"),
    "return": ("yes", "no"),
}
REQUIRED = ("business", "btype", "location", "entry_type", "reaction",
            "core_problem", "insight", "interest", "return")
TEXT = ("business", "location", "first_contact", "customer_flow", "staff_behavior",
        "bottleneck", "core_problem", "insight", "struggle", "when")
QUESTIONS = 4


def _txt(v, n=400):
    return " ".join(str(v or "").split())[:n]


def normalise_field_card(sub):
    """Returns a clean submission dict or raises ValueError with a plain message."""
    out = {"type": "field_card"}
    for k in TEXT:
        out[k] = _txt(sub.get(k))
    for k, allowed in CHOICES.items():
        v = _txt(sub.get(k), 20)
        if v and v not in allowed:
            raise ValueError("Pick one of: " + ", ".join(allowed) + " (" + k.replace("_", " ") + ")")
        out[k] = v
    for k in REQUIRED:
        if not out[k]:
            raise ValueError("Please fill in: " + k.replace("_", " "))

    asked = sub.get("asked") or []
    out["asked"] = [bool(asked[i]) if i < len(asked) else False for i in range(QUESTIONS)]
    quotes = [_txt(q, 300) for q in (sub.get("quotes") or [])[:3]]
    out["quotes"] = [q for q in quotes if q]
    if not out["quotes"]:
        raise ValueError("Write at least one exact quote, in their words.")

    try:
        out["trial_no"] = max(1, int(sub.get("trial_no") or 1))
    except (TypeError, ValueError):
        out["trial_no"] = 1
    d = _txt(sub.get("date"), 10)
    try:
        date.fromisoformat(d)
    except ValueError:
        raise ValueError("Date must be a real date.")
    out["date"] = d

    scores = {}
    for k in ("a", "t", "d"):
        raw = (sub.get("scores") or {}).get(k)
        if raw in (None, ""):
            continue
        try:
            n = int(raw)
        except (TypeError, ValueError):
            raise ValueError("Scores are whole numbers from 1 to 10.")
        if not 1 <= n <= 10:
            raise ValueError("Scores are whole numbers from 1 to 10.")
        scores[k] = n
    out["scores"] = scores

    link = _txt(sub.get("link"), 500)
    if link and not link.lower().startswith(("http://", "https://")):
        raise ValueError("The link must start with http:// or https://")
    out["link"] = link or None
    # keeps older screens (review queue, business view, evidence) working
    out["summary"] = out["core_problem"]
    return out
