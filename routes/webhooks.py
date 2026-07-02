import hashlib
import hmac
import logging

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session
from fastapi import Depends

from config import settings
from database import get_db
from models.booking import Booking
from models.lead import Lead
from utils.ghl import TAG_TO_STATUS
import services.paypal as paypal_svc

log = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_STATUS_SET = frozenset(TAG_TO_STATUS.keys())  # "lead-new", "lead-assigned", etc.

# GHL sends ALL tags on the contact, not just the newly added one.
# Pick the most advanced status so earlier tags don't overwrite progress.
_STATUS_PRIORITY: dict[str, int] = {"new": 0, "assigned": 1, "contacted": 2, "closed": 3}


def _verify_signature(body: bytes, sig_header: str | None, query_key: str | None) -> bool:
    """
    Verify the incoming request is from GHL. Two accepted methods:
    1. HMAC-SHA256 signature in x-ghl-signature header (Private Integration webhooks)
    2. Static secret passed as ?key=<secret> query param (Automation/Workflow webhooks)
    Rejects all requests when GHL_WEBHOOK_SECRET is not configured.
    """
    secret = settings.ghl_webhook_secret
    if not secret:
        log.error("GHL_WEBHOOK_SECRET is not set — rejecting all incoming webhooks")
        return False
    if sig_header:
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig_header.lower().removeprefix("sha256="))
    if query_key:
        return hmac.compare_digest(secret, query_key)
    return False


@router.post("/ghl", status_code=200)
async def ghl_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receive GHL contact events and sync lead status back to our DB.
    Auth: HMAC-SHA256 via x-ghl-signature header OR static secret via ?key= query param.
    """
    raw_body = await request.body()

    sig_header = (
        request.headers.get("x-ghl-signature")
        or request.headers.get("x-ghl-signature-256")
    )
    query_key = request.query_params.get("key")
    if not _verify_signature(raw_body, sig_header, query_key):
        log.warning("GHL webhook: invalid signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = await request.json()
    except Exception:
        log.warning("GHL webhook: malformed JSON body_len=%d content_type=%s",
                    len(raw_body), request.headers.get("content-type"))
        return {"received": True}

    log.warning("GHL webhook payload keys=%s contact_id=%r tags=%s",
                list(payload.keys()),
                payload.get("contact_id"),
                payload.get("tags"))

    contact_id: str | None = (
        payload.get("contact_id") or payload.get("contactId") or payload.get("id")
    )
    if not contact_id:
        log.warning("GHL webhook: no contactId in payload")
        return {"received": True}

    # GHL Automation webhooks send tags as a comma-separated string; Private Integration sends a list
    raw_tags = payload.get("tags") or []
    if isinstance(raw_tags, str):
        raw_tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
    incoming_tags: list[str] = raw_tags

    # GHL sends ALL tags on the contact — pick the most advanced status present
    matched_status: str | None = max(
        (TAG_TO_STATUS[tag] for tag in incoming_tags if tag in _STATUS_SET),
        key=lambda s: _STATUS_PRIORITY.get(s, -1),
        default=None,
    )

    if not matched_status:
        log.warning("GHL webhook: no matching status tag in %s", incoming_tags)
        return {"received": True}

    lead: Lead | None = db.query(Lead).filter(Lead.ghl_contact_id == contact_id).first()
    if not lead:
        log.warning("GHL webhook: no lead found for ghl_contact_id=%s", contact_id)
        return {"received": True}

    if lead.status == matched_status:
        log.warning("GHL webhook: lead %s already has status %s", lead.id, matched_status)
        return {"received": True}

    old_status = lead.status
    lead.status = matched_status

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    if matched_status == "assigned" and lead.assigned_at is None:
        lead.assigned_at = now
    elif matched_status == "contacted" and lead.contacted_at is None:
        lead.contacted_at = now
    elif matched_status == "closed" and lead.closed_at is None:
        lead.closed_at = now

    db.commit()
    log.info("GHL webhook: lead %s status %s -> %s", lead.id, old_status, matched_status)
    return {"received": True}


@router.post("/paypal", status_code=200)
async def paypal_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receive PayPal webhook events and keep booking payment/payout status in sync.
    Signature verification is performed before any DB writes.
    """
    raw_body = await request.body()
    headers = dict(request.headers)

    if not paypal_svc.verify_webhook_signature(headers, raw_body):
        log.warning("PayPal webhook: invalid signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = await request.json()
    except Exception:
        return {"received": True}

    event_type: str = payload.get("event_type", "")
    resource: dict = payload.get("resource", {})
    log.info("PayPal webhook: event_type=%s", event_type)

    if event_type == "PAYMENT.AUTHORIZATION.VOIDED":
        auth_id = resource.get("id")
        if auth_id:
            booking = db.query(Booking).filter(Booking.paypal_authorization_id == auth_id).first()
            if booking and booking.payment_status != "voided":
                booking.payment_status = "voided"
                db.commit()

    elif event_type == "PAYMENT.CAPTURE.COMPLETED":
        capture_id = resource.get("id")
        if capture_id:
            booking = db.query(Booking).filter(Booking.paypal_capture_id == capture_id).first()
            if booking and booking.payment_status != "captured":
                booking.payment_status = "captured"
                db.commit()

    elif event_type == "PAYMENT.PAYOUTS-ITEM.SUCCEEDED":
        sender_item_id = resource.get("payout_item", {}).get("sender_item_id")
        if sender_item_id:
            booking = db.query(Booking).filter(Booking.id == sender_item_id).first()
            if booking and booking.payout_status != "paid":
                booking.payout_status = "paid"
                db.commit()

    elif event_type == "PAYMENT.PAYOUTS-ITEM.FAILED":
        sender_item_id = resource.get("payout_item", {}).get("sender_item_id")
        if sender_item_id:
            booking = db.query(Booking).filter(Booking.id == sender_item_id).first()
            if booking:
                booking.payout_status = "failed"
                db.commit()
        log.error("PayPal payout failed: %s", payload)

    elif event_type == "CUSTOMER.DISPUTE.CREATED":
        log.error("PayPal dispute created: %s", payload)

    return {"received": True}
