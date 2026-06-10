from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, aliased
from typing import List, Optional

from database import get_db
from models.upgrade_request import UpgradeRequest
from models.listing import Listing
from models.user import User
from schemas.upgrade_request import UpgradeRequestAdminResponse, AdminRejectBody as UpgradeRejectBody
from schemas.listing import ListingResponse, AdminListingResponse, AdminRejectBody as ListingRejectBody
from utils.permission import require_admin

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
def approve_upgrade_request(req_id, user=Depends(require_admin), db: Session = Depends(get_db)):
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


@router.post("/upgrade-requests/{req_id}/reject", status_code=204)
def reject_upgrade_request(req_id, body: UpgradeRejectBody, user=Depends(require_admin), db: Session = Depends(get_db)):
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
def approve_listing(listing_id, user=Depends(require_admin), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.status != "pending_approval":
        raise HTTPException(status_code=409, detail="Listing not in pending state")

    listing.status = "active"
    listing.approved_by = user.id
    listing.approved_at = datetime.now(timezone.utc)
    db.commit()


@router.post("/listings/{listing_id}/archive", status_code=204)
def archive_listing(listing_id, user=Depends(require_admin), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing.status = "archived"
    listing.approved_by = user.id
    listing.approved_at = datetime.now(timezone.utc)
    db.commit()


@router.post("/listings/{listing_id}/reject", status_code=204)
def reject_listing(listing_id, body: ListingRejectBody, user=Depends(require_admin), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing.status = "rejected"
    listing.rejection_reason = body.reason
    listing.approved_by = user.id
    listing.approved_at = datetime.now(timezone.utc)
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
