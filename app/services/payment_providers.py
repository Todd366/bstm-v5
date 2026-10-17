"""Payment provider adapters.

Today every payment is confirmed by hand ("manual"): the business pays by
MyZaka / Orange Money / EFT, submits the transaction reference, staff
confirm it. A gateway (Tingg, Virtual Pay, DPO, ...) or an automation
(an SMS-forwarding phone that reads MyZaka/Orange confirmations) plugs in
by posting signed events to POST /webhooks/{provider}.

Adapter contract (a provider is anything with):
    name                      unique lowercase id, also the URL segment
    verify_webhook(headers, body_bytes) -> dict
        Raises ValueError unless the request is authentic. Returns
        {"invoice_reference", "provider_ref", "amount", "method"}.
Events are idempotent: (provider, provider_ref) is unique in `payments`,
so a retried webhook never double-credits an invoice.
"""

import hashlib
import hmac
import json
import os

from app.core.errors import Forbidden


class Provider:
    name = ""

    def verify_webhook(self, headers, body):
        raise ValueError("This provider does not accept webhooks")


class ManualProvider(Provider):
    name = "manual"


class SignedWebhookProvider(Provider):
    """Generic provider: body is JSON, `X-Signature` is the hex
    HMAC-SHA256 of the raw body keyed with BSTM_WEBHOOK_SECRET_<NAME>."""

    def __init__(self, name):
        self.name = name

    def _secret(self):
        return os.getenv("BSTM_WEBHOOK_SECRET_" + self.name.upper().replace("-", "_"), "")

    def verify_webhook(self, headers, body):
        secret = self._secret()

        if not secret:
            raise Forbidden("Provider is not configured")

        provided = (headers.get("x-signature") or "").strip().lower()
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

        if not provided or not hmac.compare_digest(provided, expected):
            raise Forbidden("Invalid signature")

        try:
            event = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise ValueError("Invalid event body")

        if not isinstance(event, dict):
            raise ValueError("Invalid event body")

        return {
            "invoice_reference": event.get("invoice_reference"),
            "provider_ref": event.get("provider_ref"),
            "amount": event.get("amount"),
            "method": event.get("method") or "Other",
        }


PROVIDERS = {
    "manual": ManualProvider(),
    "sms-bridge": SignedWebhookProvider("sms-bridge"),
    "gateway": SignedWebhookProvider("gateway"),
}


def get_provider(name):
    provider = PROVIDERS.get((name or "").lower())

    if provider is None:
        raise ValueError("Provider not found")

    return provider
