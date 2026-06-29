from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, aliased
from typing import List, Optional
from uuid import UUID

from config import settings
from database import get_db
from models.activity_log import ActivityLog
from models.site_settings import SiteSettings
from models.upgrade_request import UpgradeRequest
from models.listing import Listing
from models.listing_edit import ListingEdit
from models.listing_event import ListingEvent
from models.user import User
from models.deal_request import DealRequest
from schemas.auth import CreateAdminUserBody
from schemas.upgrade_request import UpgradeRequestAdminResponse, AdminRejectBody as UpgradeRejectBody
from schemas.listing import ListingResponse, AdminListingResponse, AdminRejectBody as ListingRejectBody
from schemas.deal_request import DealRequestResponse, DealRequestRejectBody
from schemas.listing_edit import ListingEditResponse, ListingEditRejectBody
from schemas.listing_event import ListingEventResponse
from utils.permission import require_admin
from utils.security import hash_password
from utils.email import (
    send_listing_approved_email,
    send_listing_rejected_email,
    send_upgrade_approved_email,
    send_upgrade_rejected_email,
)


def _log(db: Session, event_type: str, description: str, actor_id=None):
    db.add(ActivityLog(event_type=event_type, description=description, actor_id=actor_id))


def _listing_event(
    db: Session,
    listing_id,
    event_type: str,
    actor_id=None,
    note: str = None,
    snapshot_before: dict = None,
    snapshot_after: dict = None,
):
    db.add(ListingEvent(
        listing_id=listing_id,
        event_type=event_type,
        actor_id=actor_id,
        note=note,
        snapshot_before=snapshot_before,
        snapshot_after=snapshot_after,
    ))

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Upgrade Requests ──────────────────────────────────────────────────────────

@router.get("/upgrade-requests", response_model=List[UpgradeRequestAdminResponse])
def list_upgrade_requests(status: Optional[str] = Query(None), user=Depends(require_admin), db: Session = Depends(get_db)):
    Reviewer = aliased(User)
    q = (
        db.query(UpgradeRequest, User, Reviewer)
        .join(User, User.id == UpgradeRequest.user_id)
        .outerjoin(Reviewer, Reviewer.id == UpgradeRequest.reviewed_by)
    )
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
            reviewed_by_name=reviewer.display_name or reviewer.email if reviewer else None,
            reviewed_at=req.reviewed_at,
            license_number=req.license_number,
            territory=req.territory,
            years_experience=req.years_experience,
            specialties=req.specialties,
            bio=req.bio,
        )
        for req, u, reviewer in rows
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

    role_label = req.requested_role.capitalize()
    name = target_user.display_name or target_user.email if target_user else str(req.user_id)
    _log(db, "upgrade_approved", f"New {role_label} approved: {name}", actor_id=user.id)
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
    target_user = db.query(User).filter(User.id == req.user_id).first()
    name = target_user.display_name or target_user.email if target_user else str(req.user_id)
    _log(db, "upgrade_rejected", f"Upgrade request rejected: {name}", actor_id=user.id)
    db.commit()
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
    _log(db, "listing_approved", f"Listing approved: {listing.title}", actor_id=user.id)
    _listing_event(db, listing.id, "approved", actor_id=user.id)
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
    _log(db, "listing_archived", f"Listing archived: {listing.title}", actor_id=user.id)
    _listing_event(db, listing.id, "archived", actor_id=user.id)
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
    _log(db, "listing_rejected", f"Listing rejected: {listing.title}", actor_id=user.id)
    _listing_event(db, listing.id, "rejected", actor_id=user.id, note=body.reason)
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
    "tags", "video_links", "tour_3d_url", "utilities", "included_utilities",
    "association_fee", "deposit_policy",
    "co_listing_enabled", "co_listing_brokerage", "co_listing_agent_name",
    "co_listing_agent_contact", "co_listing_commission_split",
    "co_listing_notes", "co_listing_status",
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
    before = _listing_snapshot(listing)
    _NOT_NULL_BOOLEANS = {"seller_financing", "hoa", "tax_exempt", "gated_community", "co_listing_enabled"}
    for field in EDIT_FIELDS:
        if field in proposed:
            val = proposed[field]
            if val is None and field in _NOT_NULL_BOOLEANS:
                continue
            setattr(listing, field, val)

    listing.updated_at = datetime.now(timezone.utc)
    edit.status = "approved"
    edit.reviewed_by = user.id
    edit.reviewed_at = datetime.now(timezone.utc)
    _log(db, "edit_approved", f"Listing edit approved: {listing.title}", actor_id=user.id)
    _listing_event(db, listing.id, "edit_approved", actor_id=user.id, snapshot_before=before, snapshot_after=proposed)
    db.commit()


@router.post("/listing-edits/{edit_id}/reject", status_code=204)
def reject_listing_edit(edit_id: UUID, body: ListingEditRejectBody, user=Depends(require_admin), db: Session = Depends(get_db)):
    edit = db.query(ListingEdit).filter(ListingEdit.id == edit_id).first()
    if not edit:
        raise HTTPException(status_code=404, detail="Edit not found")
    if edit.status != "pending":
        raise HTTPException(status_code=409, detail="Edit already reviewed")

    listing = db.query(Listing).filter(Listing.id == edit.listing_id).first()
    edit.status = "rejected"
    edit.reviewed_by = user.id
    edit.reviewed_at = datetime.now(timezone.utc)
    edit.rejection_reason = body.reason
    _log(db, "edit_rejected", f"Listing edit rejected", actor_id=user.id)
    _listing_event(
        db, edit.listing_id, "edit_rejected", actor_id=user.id,
        note=body.reason, snapshot_after=edit.proposed_data,
    )
    db.commit()


# ── Listing History ───────────────────────────────────────────────────────────

@router.get("/listings/{listing_id}/history", response_model=List[ListingEventResponse])
def get_listing_history(listing_id: UUID, user=Depends(require_admin), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    Actor = aliased(User)
    rows = (
        db.query(ListingEvent, Actor)
        .outerjoin(Actor, Actor.id == ListingEvent.actor_id)
        .filter(ListingEvent.listing_id == listing_id)
        .order_by(ListingEvent.created_at.desc())
        .all()
    )
    return [
        ListingEventResponse(
            id=ev.id,
            listing_id=ev.listing_id,
            event_type=ev.event_type,
            actor_name=actor.display_name if actor else None,
            actor_email=actor.email if actor else None,
            note=ev.note,
            snapshot_before=ev.snapshot_before,
            snapshot_after=ev.snapshot_after,
            created_at=ev.created_at,
        )
        for ev, actor in rows
    ]


# ── Users ─────────────────────────────────────────────────────────────────────

_VALID_ROLES    = {'buyer', 'owner', 'realtor', 'admin'}
_VALID_STATUSES = {'active', 'suspended'}


@router.get("/users")
def list_users(role: Optional[str] = Query(None), status: Optional[str] = Query(None), user=Depends(require_admin), db: Session = Depends(get_db)):
    if role and role not in _VALID_ROLES:
        raise HTTPException(status_code=422, detail="Invalid role")
    if status and status not in _VALID_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid status")
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    if status:
        q = q.filter(User.status == status)
    return [
        {
            "id": str(u.id), "user_code": u.user_code,
            "email": u.email, "role": u.role, "status": u.status,
            "display_name": u.display_name, "phone": u.phone,
            "created_at": u.created_at, "avatar_url": u.avatar_url,
        }
        for u in q.order_by(User.created_at.desc()).all()
    ]


_CREATEABLE_ROLES = {'buyer', 'owner', 'realtor'}

@router.post("/users", status_code=201)
def create_user(body: CreateAdminUserBody, admin=Depends(require_admin), db: Session = Depends(get_db)):
    if body.role not in _CREATEABLE_ROLES:
        raise HTTPException(status_code=422, detail="Invalid role")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    new_user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        role=body.role,
        status="active",
        email_verified=True,
    )
    db.add(new_user)
    _log(db, "user_created", f"New user created: {body.display_name or body.email}", actor_id=admin.id)
    db.commit()
    db.refresh(new_user)
    return {
        "id": str(new_user.id), "user_code": new_user.user_code,
        "email": new_user.email, "role": new_user.role, "status": new_user.status,
        "display_name": new_user.display_name, "phone": new_user.phone,
        "created_at": new_user.created_at, "avatar_url": None,
    }


@router.put("/users/{user_id}/suspend", status_code=204)
def suspend_user(user_id: str, user=Depends(require_admin), db: Session = Depends(get_db)):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if str(target.id) == str(user.id):
        raise HTTPException(status_code=400, detail="You cannot suspend your own account")
    target.status = "suspended"
    db.commit()


@router.put("/users/{user_id}/unsuspend", status_code=204)
def unsuspend_user(user_id: str, user=Depends(require_admin), db: Session = Depends(get_db)):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    target.status = "active"
    db.commit()


_CHANGEABLE_ROLES = {"buyer", "owner", "realtor"}

class ChangeRoleBody(BaseModel):
    role: str

@router.put("/users/{user_id}/role", status_code=204)
def change_user_role(user_id: str, body: ChangeRoleBody, admin=Depends(require_admin), db: Session = Depends(get_db)):
    if body.role not in _CHANGEABLE_ROLES:
        raise HTTPException(status_code=422, detail="Role must be buyer, owner, or realtor")
    target = db.query(User).filter(User.id == UUID(user_id)).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if str(target.id) == str(admin.id):
        raise HTTPException(status_code=400, detail="You cannot change your own role")
    if target.role == "admin":
        raise HTTPException(status_code=403, detail="Cannot change the role of an admin account")
    target.role = body.role
    db.commit()


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats")
def get_admin_stats(user=Depends(require_admin), db: Session = Depends(get_db)):
    active_listings  = db.query(func.count(Listing.id)).filter(Listing.status == "active").scalar() or 0
    pending_listings = db.query(func.count(Listing.id)).filter(Listing.status == "pending_approval").scalar() or 0
    total_users      = db.query(func.count(User.id)).scalar() or 0
    return {
        "active_listings": active_listings,
        "pending_listings": pending_listings,
        "total_users": total_users,
    }


# ── Activity Log ──────────────────────────────────────────────────────────────

# ── Deal Requests ─────────────────────────────────────────────────────────────

@router.get("/deal-requests", response_model=List[DealRequestResponse])
def list_deal_requests(status: Optional[str] = Query(None), user=Depends(require_admin), db: Session = Depends(get_db)):
    Requester = aliased(User)
    Reviewer  = aliased(User)
    q = (
        db.query(DealRequest, Listing, Requester, Reviewer)
        .join(Listing,   Listing.id   == DealRequest.listing_id)
        .join(Requester, Requester.id == DealRequest.requested_by)
        .outerjoin(Reviewer, Reviewer.id == DealRequest.reviewed_by)
    )
    if status:
        q = q.filter(DealRequest.status == status)
    rows = q.order_by(DealRequest.created_at.desc()).all()
    return [
        DealRequestResponse(
            id=req.id,
            listing_id=req.listing_id,
            listing_title=listing.title,
            listing_location=listing.location,
            listing_thumbnail=listing.images[0] if listing.images else None,
            requested_by_name=requester.display_name,
            requested_by_email=requester.email,
            discount_value=float(req.discount_value),
            discount_type=req.discount_type,
            message=req.message,
            status=req.status,
            rejection_reason=req.rejection_reason,
            reviewed_by_name=reviewer.display_name or reviewer.email if reviewer else None,
            reviewed_at=req.reviewed_at,
            created_at=req.created_at,
        )
        for req, listing, requester, reviewer in rows
    ]


@router.post("/deal-requests/{req_id}/approve", status_code=204)
def approve_deal_request(req_id: UUID, user=Depends(require_admin), db: Session = Depends(get_db)):
    req = db.query(DealRequest).filter(DealRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Deal request not found")
    if req.status != "pending":
        raise HTTPException(status_code=409, detail="Request already reviewed")

    listing = db.query(Listing).filter(Listing.id == req.listing_id).first()
    if not listing or listing.status != "active":
        raise HTTPException(status_code=400, detail="Listing is no longer active")

    listing.is_deal = True
    listing.deal_discount_value = req.discount_value
    listing.deal_discount_type = req.discount_type

    req.status = "approved"
    req.reviewed_by = user.id
    req.reviewed_at = datetime.now(timezone.utc)

    discount_label = f"−{req.discount_value}%" if req.discount_type == "pct" else f"−${req.discount_value:,.0f}"
    _log(db, "deal_approved", f"Deal of the Week set: {listing.title} ({discount_label})", actor_id=user.id)
    db.commit()


@router.post("/deal-requests/{req_id}/reject", status_code=204)
def reject_deal_request(req_id: UUID, body: DealRequestRejectBody, user=Depends(require_admin), db: Session = Depends(get_db)):
    req = db.query(DealRequest).filter(DealRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Deal request not found")
    if req.status != "pending":
        raise HTTPException(status_code=409, detail="Request already reviewed")

    req.status = "rejected"
    req.rejection_reason = body.reason
    req.reviewed_by = user.id
    req.reviewed_at = datetime.now(timezone.utc)

    listing = db.query(Listing).filter(Listing.id == req.listing_id).first()
    _log(db, "deal_rejected", f"Deal request rejected: {listing.title if listing else req.listing_id}", actor_id=user.id)
    db.commit()


@router.post("/listings/{listing_id}/clear-deal", status_code=204)
def clear_listing_deal(listing_id: UUID, user=Depends(require_admin), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing.is_deal = False
    listing.deal_discount_value = None
    listing.deal_discount_type = 'pct'
    _log(db, "deal_cleared", f"Deal of the Week cleared: {listing.title}", actor_id=user.id)
    db.commit()


class SetDealBody(BaseModel):
    discount_value: Optional[float] = None
    discount_type: str = 'pct'


@router.post("/listings/{listing_id}/set-deal", status_code=204)
def set_listing_deal(listing_id: UUID, body: SetDealBody, user=Depends(require_admin), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.status != "active":
        raise HTTPException(status_code=400, detail="Listing must be active to set as Deal of the Week")
    if listing.is_deal:
        raise HTTPException(status_code=409, detail="Listing is already a Deal of the Week")
    listing.is_deal = True
    listing.deal_discount_value = body.discount_value
    listing.deal_discount_type = body.discount_type or 'pct'
    if body.discount_value:
        discount_label = f"−{body.discount_value}%" if body.discount_type == "pct" else f"−${body.discount_value:,.0f}"
    else:
        discount_label = "no discount"
    _log(db, "deal_approved", f"Deal of the Week set: {listing.title} ({discount_label})", actor_id=user.id)
    db.commit()


@router.get("/settings")
def get_settings(user=Depends(require_admin), db: Session = Depends(get_db)):
    row = db.query(SiteSettings).filter(SiteSettings.id == 1).first()
    data = row.data if row else {}
    return {"notify_email": data.get("notify_email", ""), "updated_at": row.updated_at if row else None}


class PlatformSettingsBody(BaseModel):
    notify_email: Optional[str] = None


@router.put("/settings", status_code=204)
def update_settings(body: PlatformSettingsBody, user=Depends(require_admin), db: Session = Depends(get_db)):
    row = db.query(SiteSettings).filter(SiteSettings.id == 1).first()
    if row is None:
        row = SiteSettings(id=1, data={})
        db.add(row)
    new_data = dict(row.data or {})
    if body.notify_email is not None:
        new_data["notify_email"] = body.notify_email.strip()
    row.data = new_data
    db.commit()


@router.get("/activity-log")
def get_activity_log(limit: int = Query(20, le=50), user=Depends(require_admin), db: Session = Depends(get_db)):
    entries = (
        db.query(ActivityLog)
        .order_by(ActivityLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "description": e.description,
            "created_at": e.created_at,
        }
        for e in entries
    ]
