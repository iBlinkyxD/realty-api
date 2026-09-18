"""
PayPal REST API v2 client.

Reads PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_MODE (sandbox|live)
and PAYPAL_WEBHOOK_ID from environment via config.settings.

All functions raise RuntimeError when credentials are absent and
HTTPStatusError on unexpected PayPal API responses.
"""
import hashlib
import hmac
import json
import logging
import threading
import time
from typing import Any

import httpx

from config import settings

log = logging.getLogger(__name__)

_BASE = {
    "sandbox": "https://api-m.sandbox.paypal.com",
    "live":    "https://api-m.paypal.com",
}

# Simple in-process token cache — refreshed when within 60 s of expiry
_token_lock = threading.Lock()
_cached_token: str | None = None
_token_expires_at: float = 0.0


def _base_url() -> str:
    mode = getattr(settings, "paypal_mode", "sandbox") or "sandbox"
    return _BASE.get(mode, _BASE["sandbox"])


def _credentials() -> tuple[str, str]:
    client_id = getattr(settings, "paypal_client_id", None)
    client_secret = getattr(settings, "paypal_client_secret", None)
    if not client_id or not client_secret:
        raise RuntimeError(
            "PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET must be set in Railway env vars before using PayPal features."
        )
    return client_id, client_secret


def get_access_token() -> str:
    global _cached_token, _token_expires_at
    with _token_lock:
        if _cached_token and time.monotonic() < _token_expires_at - 60:
            return _cached_token
        client_id, client_secret = _credentials()
        r = httpx.post(
            f"{_base_url()}/v1/oauth2/token",
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        _cached_token = data["access_token"]
        _token_expires_at = time.monotonic() + data.get("expires_in", 3600)
        return _cached_token


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json",
    }


def _post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    r = httpx.post(f"{_base_url()}{path}", headers=_headers(), json=body, timeout=15)
    r.raise_for_status()
    return r.json() if r.content else {}


def _get(path: str) -> dict[str, Any]:
    r = httpx.get(f"{_base_url()}{path}", headers=_headers(), timeout=15)
    r.raise_for_status()
    return r.json()


def create_order(amount_usd: float, booking_ref: str) -> dict[str, str]:
    """Create a PayPal order with intent=AUTHORIZE. Returns { order_id }."""
    data = _post("/v2/checkout/orders", {
        "intent": "AUTHORIZE",
        "purchase_units": [{
            "reference_id": booking_ref,
            "amount": {
                "currency_code": "USD",
                "value": f"{amount_usd:.2f}",
            },
        }],
    })
    return {"order_id": data["id"]}


def authorize_order(order_id: str) -> dict[str, str]:
    """
    Authorize an approved PayPal order (buyer has approved on PayPal).
    Returns { authorization_id, amount_usd, currency }.
    """
    data = _post(f"/v2/checkout/orders/{order_id}/authorize", {})
    auth = (
        data.get("purchase_units", [{}])[0]
        .get("payments", {})
        .get("authorizations", [{}])[0]
    )
    auth_id = auth.get("id")
    if not auth_id:
        raise RuntimeError(f"PayPal authorize_order: no authorization_id in response for order {order_id}")
    amount = auth.get("amount", {})
    return {
        "authorization_id": auth_id,
        "amount_usd": float(amount.get("value", 0)),
        "currency": amount.get("currency_code", ""),
    }


def capture_authorization(authorization_id: str) -> dict[str, str]:
    """Capture a previously authorized payment. Returns { capture_id }."""
    data = _post(f"/v2/payments/authorizations/{authorization_id}/capture", {})
    return {"capture_id": data["id"], "status": data.get("status", "")}


def void_authorization(authorization_id: str) -> None:
    """Void an authorization — guest is never charged."""
    r = httpx.post(
        f"{_base_url()}/v2/payments/authorizations/{authorization_id}/void",
        headers=_headers(),
        timeout=15,
    )
    r.raise_for_status()


def create_payout(receiver_email: str, amount_usd: float, booking_id: str) -> str:
    """
    Send a payout to the owner via PayPal Payouts API.
    Requires Payouts API approval on the business account.
    Returns payout_batch_id.
    """
    data = _post("/v1/payments/payouts", {
        "sender_batch_header": {
            "sender_batch_id": f"booking-{booking_id}",
            "email_subject": "Your I Love DR Realty payout",
        },
        "items": [{
            "recipient_type": "EMAIL",
            "amount": {"value": f"{amount_usd:.2f}", "currency": "USD"},
            "receiver": receiver_email,
            "sender_item_id": booking_id,
        }],
    })
    return data["batch_header"]["payout_batch_id"]


def refund_capture(capture_id: str, amount_usd: float) -> str:
    """Issue a full refund on a captured payment. Returns refund_id."""
    data = _post(f"/v2/payments/captures/{capture_id}/refund", {
        "amount": {"value": f"{amount_usd:.2f}", "currency_code": "USD"},
    })
    return data["id"]


def verify_webhook_signature(headers: dict[str, str], raw_body: bytes) -> bool:
    """
    Verify an incoming PayPal webhook using the Verify Webhook Signature API.
    Falls back to False on any error so we reject unverified requests.
    """
    webhook_id = getattr(settings, "paypal_webhook_id", None)
    if not webhook_id:
        log.error("PAYPAL_WEBHOOK_ID not set — rejecting PayPal webhook")
        return False
    try:
        payload = {
            "auth_algo":          headers.get("paypal-auth-algo", ""),
            "cert_url":           headers.get("paypal-cert-url", ""),
            "transmission_id":    headers.get("paypal-transmission-id", ""),
            "transmission_sig":   headers.get("paypal-transmission-sig", ""),
            "transmission_time":  headers.get("paypal-transmission-time", ""),
            "webhook_id":         webhook_id,
            "webhook_event":      json.loads(raw_body),
        }
        r = httpx.post(
            f"{_base_url()}/v1/notifications/verify-webhook-signature",
            headers=_headers(),
            json=payload,
            timeout=10,
        )
        r.raise_for_status()
        return r.json().get("verification_status") == "SUCCESS"
    except Exception:
        log.exception("PayPal webhook signature verification failed")
        return False
