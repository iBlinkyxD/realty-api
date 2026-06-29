import hashlib
import hmac
import logging

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session
from fastapi import Depends

from config import settings
from database import get_db
from models.lead import Lead
from utils.ghl import TAG_TO_STATUS

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
