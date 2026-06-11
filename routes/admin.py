from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, aliased
from typing import List, Optional
from uuid import UUID

from config import settings
from database import get_db
from models.upgrade_request import UpgradeRequest
from models.listing import Listing
from models.listing_edit import ListingEdit
from models.user import User
from schemas.upgrade_request import UpgradeRequestAdminResponse, AdminRejectBody as UpgradeRejectBody
from schemas.listing import ListingResponse, AdminListingResponse, AdminRejectBody as ListingRejectBody
from schemas.listing_edit import ListingEditResponse, ListingEditRejectBody
from utils.permission import require_admin
from utils.email import (
    send_listing_approved_email,
    send_listing_rejected_email,
    send_upgrade_approved_email,
    send_upgrade_rejected_email,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Upgrade Requests ──────────────────────────────────────────────────────────

@router.get("/upgrade-requests", response_model=List[UpgradeRequestAdminResponse])
def list_upgrade_requests(status: Optional[str] = Query(None), user=Depends(require_admin), db: Session = Depends(get_db)):
    q = db.query(UpgradeRequest, User).join(User, User.id == UpgradeRequest.user_id)
    if status:
        q = q.filter(UpgradeRequest.status == status)
    rows = q.order_by(UpgradeRequest.created_at.desc()).all()
    return [
        UpgradeRequestAdminResponse(
            id=req.id,
            user_id=req.user_id,
            user_email=u.email,
            user_display_name=u.display_name,
            requested_role=req.requested_role,
            status=req.status,
            rejection_reason=req.rejection_reason,
            created_at=req.created_at,
        )
        for req, u in rows
    ]


@router.post("/upgrade-requests/{req_id}/approve", status_code=204)
def approve_upgrade_request(req_id: UUID, user=Depends(require_admin), db: Session = Depends(get_db)):
    req = db.query(UpgradeRequest).filter(UpgradeRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "pending":
        raise HTTPException(status_code=409, detail="Request already reviewed")

    req.status = "approved"
    req.reviewed_by = user.id
    req.reviewed_at = datetime.now(timezone.utc)

    target_user = db.query(User).filter(User.id == req.user_id).first()
    if target_user:
        target_user.role = req.requested_role

    db.commit()
    if target_user:
        try:
            send_upgrade_approved_email(target_user.email, target_user.display_name or target_user.email, req.requested_role)
        except Exception:
            pass


@router.post("/upgrade-requests/{req_id}/reject", status_code=204)
def reject_upgrade_request(req_id: UUID, body: UpgradeRejectBody, user=Depends(require_admin), db: Session = Depends(get_db)):
    req = db.query(UpgradeRequest).filter(UpgradeRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "pending":
        raise HTTPException(status_code=409, detail="Request already reviewed")

    req.status = "rejected"
    req.reviewed_by = user.id
    req.reviewed_at = datetime.now(timezone.utc)
    req.rejection_reason = body.reason
    db.commit()
    target_user = db.query(User).filter(User.id == req.user_id).first()
    if target_user:
        try:
            send_upgrade_rejected_email(target_user.email, target_user.display_name or target_user.email, body.reason)
        except Exception:
            pass


# ── Listings ──────────────────────────────────────────────────────────────────

@router.get("/listings", response_model=List[AdminListingResponse])
def list_all_listings(status: Optional[str] = Query(None), user=Depends(require_admin), db: Session = Depends(get_db)):
    Submitter = aliased(User)
    Reviewer  = aliased(User)
    q = (
        db.query(Listing, Submitter, Reviewer)
        .join(Submitter, Submitter.id == Listing.submitted_by)
        .outerjoin(Reviewer, Reviewer.id == Listing.approved_by)
    )
    if status:
        q = q.filter(Listing.status == status)
    rows = q.order_by(Listing.created_at.desc()).all()
    return [
        AdminListingResponse(
            **{c.key: getattr(listing, c.key) for c in Listing.__table__.columns},
            submitted_by_name=submitter.display_name,
            submitted_by_email=submitter.email,
            reviewed_by_name=reviewer.display_name if reviewer else None,
            reviewed_by_email=reviewer.email if reviewer else None,
            reviewed_at=listing.approved_at,
        )
        for listing, submitter, reviewer in rows
    ]


@router.post("/listings/{listing_id}/approve", status_code=204)
def approve_listing(listing_id: UUID, user=Depends(require_admin), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.status != "pending_approval":
        raise HTTPException(status_code=409, detail="Listing not in pending state")

    listing.status = "active"
    listing.approved_by = user.id
    listing.approved_at = datetime.now(timezone.utc)
    db.commit()
    submitter = db.query(User).filter(User.id == listing.submitted_by).first()
    if submitter:
        try:
            listing_url = f"{settings.landing_url}/property?id={listing.id}"
            send_listing_approved_email(submitter.email, submitter.display_name or submitter.email, listing.title, listing_url)
        except Exception:
            pass


@router.post("/listings/{listing_id}/archive", status_code=204)
def archive_listing(listing_id: UUID, user=Depends(require_admin), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing.status = "archived"
    listing.approved_by = user.id
    listing.approved_at = datetime.now(timezone.utc)
    db.commit()


@router.post("/listings/{listing_id}/reject", status_code=204)
def reject_listing(listing_id: UUID, body: ListingRejectBody, user=Depends(require_admin), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing.status = "rejected"
    listing.rejection_reason = body.reason
    listing.approved_by = user.id
    listing.approved_at = datetime.now(timezone.utc)
    db.commit()
    submitter = db.query(User).filter(User.id == listing.submitted_by).first()
    if submitter:
        try:
            send_listing_rejected_email(submitter.email, submitter.display_name or submitter.email, listing.title, body.reason)
        except Exception:
            pass


# ── Listing Edits ─────────────────────────────────────────────────────────────

EDIT_FIELDS = [
    "title", "description", "type", "transaction", "price", "location",
    "bedrooms", "bathrooms", "area_sqft", "lot_size_sqft", "roi",
    "seller_financing", "hoa", "hoa_fee", "tax_exempt", "gated_community",
    "construction_status", "year_built", "features", "maps_url",
    "latitude", "longitude", "tag", "images",
]


def _listing_snapshot(listing: Listing) -> dict:
    snap = {}
    for field in EDIT_FIELDS:
        val = getattr(listing, field, None)
        if isinstance(val, Decimal):
            val = float(val)
        snap[field] = val
    return snap


@router.get("/listing-edits", response_model=List[ListingEditResponse])
def list_listing_edits(user=Depends(require_admin), db: Session = Depends(get_db)):
    Submitter = aliased(User)
    rows = (
        db.query(ListingEdit, Listing, Submitter)
        .join(Listing, Listing.id == ListingEdit.listing_id)
        .join(Submitter, Submitter.id == ListingEdit.submitted_by)
        .filter(ListingEdit.status == "pending")
        .order_by(ListingEdit.submitted_at.asc())
        .all()
    )
    return [
        ListingEditResponse(
            id=edit.id,
            listing_id=edit.listing_id,
            listing_title=listing.title,
            listing_location=listing.location,
            listing_thumbnail=(listing.images or [None])[0],
            submitted_by_name=submitter.display_name,
            submitted_by_email=submitter.email,
            submitted_at=edit.submitted_at,
            status=edit.status,
            current_data=_listing_snapshot(listing),
            proposed_data=edit.proposed_data,
            rejection_reason=edit.rejection_reason,
        )
        for edit, listing, submitter in rows
    ]


@router.post("/listing-edits/{edit_id}/approve", status_code=204)
def approve_listing_edit(edit_id: UUID, user=Depends(require_admin), db: Session = Depends(get_db)):
    edit = db.query(ListingEdit).filter(ListingEdit.id == edit_id).first()
    if not edit:
        raise HTTPException(status_code=404, detail="Edit not found")
    if edit.status != "pending":
        raise HTTPException(status_code=409, detail="Edit already reviewed")

    listing = db.query(Listing).filter(Listing.id == edit.listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    proposed = edit.proposed_data or {}
    for field in EDIT_FIELDS:
        if field in proposed:
            setattr(listing, field, proposed[field])

    listing.updated_at = datetime.now(timezone.utc)
    edit.status = "approved"
    edit.reviewed_by = user.id
    edit.reviewed_at = datetime.now(timezone.utc)
    db.commit()


@router.post("/listing-edits/{edit_id}/reject", status_code=204)
def reject_listing_edit(edit_id: UUID, body: ListingEditRejectBody, user=Depends(require_admin), db: Session = Depends(get_db)):
    edit = db.query(ListingEdit).filter(ListingEdit.id == edit_id).first()
    if not edit:
        raise HTTPException(status_code=404, detail="Edit not found")
    if edit.status != "pending":
        raise HTTPException(status_code=409, detail="Edit already reviewed")

    edit.status = "rejected"
    edit.reviewed_by = user.id
    edit.reviewed_at = datetime.now(timezone.utc)
    edit.rejection_reason = body.reason
    db.commit()


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users")
def list_users(role: Optional[str] = Query(None), status: Optional[str] = Query(None), user=Depends(require_admin), db: Session = Depends(get_db)):
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    if status:
        q = q.filter(User.status == status)
    return [
        {"id": str(u.id), "email": u.email, "role": u.role, "status": u.status, "display_name": u.display_name, "created_at": u.created_at}
        for u in q.order_by(User.created_at.desc()).all()
    ]
