from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, timezone

from database import get_db
from models.lead import Lead
from models.user import User
from models.listing import Listing
from utils.auth import get_current_user, get_optional_user
from utils.permission import require_admin
from utils.limiter import limiter
from utils.email import send_upgrade_approved_email, send_realtor_assigned_owner_email

router = APIRouter(tags=["leads"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class LeadCreate(BaseModel):
    type: str = Field(default="property_inquiry")  # property_inquiry | buyer_interest | seller_interest
    name: str = Field(max_length=200)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=50)
    message: Optional[str] = None
    property_id: Optional[str] = None


class LeadResponse(BaseModel):
    id: str
    type: str
    name: str
    email: str
    phone: Optional[str]
    message: Optional[str]
    property_id: Optional[str]
    property_title: Optional[str]
    listing_realtor_id: Optional[str]
    listing_realtor_name: Optional[str]
    from_user_id: Optional[str]
    from_user_code: Optional[str]
    from_user_name: Optional[str]
    from_user_avatar_url: Optional[str]
    assigned_realtor_id: Optional[str]
    assigned_realtor_name: Optional[str]
    status: str
    created_at: datetime
    assigned_at: Optional[datetime]
    contacted_at: Optional[datetime]
    closed_at: Optional[datetime]

    class Config:
        from_attributes = True


class AssignBody(BaseModel):
    realtor_id: str


class StatusBody(BaseModel):
    status: str  # new | assigned | contacted | closed


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_realtor(user):
    if user.role not in ("realtor", "admin"):
        raise HTTPException(status_code=403, detail="Realtor access required")


def _apply_status_timestamp(lead: Lead, status: str) -> None:
    now = datetime.now(timezone.utc)
    if status == "assigned" and lead.assigned_at is None:
        lead.assigned_at = now
    elif status == "contacted" and lead.contacted_at is None:
        lead.contacted_at = now
    elif status == "closed" and lead.closed_at is None:
        lead.closed_at = now


def _build_response(lead: Lead, db: Session) -> LeadResponse:
    property_title = None
    listing_realtor_id = None
    listing_realtor_name = None
    if lead.property_id:
        listing = db.query(Listing).filter(Listing.id == lead.property_id).first()
        if listing:
            property_title = listing.title
            if listing.submitted_by:
                agent = db.query(User).filter(User.id == listing.submitted_by).first()
                if agent and agent.role in ("realtor", "admin"):
                    listing_realtor_id = str(agent.id)
                    listing_realtor_name = agent.display_name or agent.email

    assigned_realtor_name = None
    if lead.assigned_realtor_id:
        realtor = db.query(User).filter(User.id == lead.assigned_realtor_id).first()
        if realtor:
            assigned_realtor_name = realtor.display_name or realtor.email

    from_user_code = None
    from_user_name = None
    from_user_avatar_url = None
    if lead.from_user_id:
        from_user = db.query(User).filter(User.id == lead.from_user_id).first()
        if from_user:
            from_user_code = str(from_user.user_code) if from_user.user_code is not None else None
            from_user_name = from_user.display_name or from_user.email
            from_user_avatar_url = from_user.avatar_url

    return LeadResponse(
        id=str(lead.id),
        type=lead.type,
        name=lead.name,
        email=lead.email,
        phone=lead.phone,
        message=lead.message,
        property_id=str(lead.property_id) if lead.property_id else None,
        property_title=property_title,
        listing_realtor_id=listing_realtor_id,
        listing_realtor_name=listing_realtor_name,
        from_user_id=str(lead.from_user_id) if lead.from_user_id else None,
        from_user_code=from_user_code,
        from_user_name=from_user_name,
        from_user_avatar_url=from_user_avatar_url,
        assigned_realtor_id=str(lead.assigned_realtor_id) if lead.assigned_realtor_id else None,
        assigned_realtor_name=assigned_realtor_name,
        status=lead.status,
        created_at=lead.created_at,
        assigned_at=lead.assigned_at,
        contacted_at=lead.contacted_at,
        closed_at=lead.closed_at,
    )


# ── Public endpoints ──────────────────────────────────────────────────────────

@router.post("/leads", status_code=201)
@limiter.limit("10/minute")
def create_lead(
    request: Request,
    body: LeadCreate,
    db: Session = Depends(get_db),
    user=Depends(get_optional_user),
):
    lead = Lead(
        type=body.type,
        name=body.name,
        email=body.email,
        phone=body.phone,
        message=body.message,
        property_id=UUID(body.property_id) if body.property_id else None,
        from_user_id=user.id if user else None,
        status="new",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return {"id": str(lead.id), "status": lead.status}


# Legacy capture endpoint — keeps existing callers working
@router.post("/leads/capture", status_code=201)
@limiter.limit("5/minute")
def capture_lead(
    request: Request,
    body: LeadCreate,
    db: Session = Depends(get_db),
):
    lead = Lead(
        type=body.type or "buyer_interest",
        name=body.name,
        email=body.email,
        phone=body.phone,
        message=body.message,
        status="new",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return {"id": str(lead.id), "status": "new"}


# ── Buyer ─────────────────────────────────────────────────────────────────────

@router.get("/leads/mine", response_model=List[LeadResponse])
def get_my_leads(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    leads = (
        db.query(Lead)
        .filter(Lead.from_user_id == user.id)
        .order_by(Lead.created_at.desc())
        .all()
    )
    return [_build_response(l, db) for l in leads]


# ── Realtor ───────────────────────────────────────────────────────────────────

@router.get("/realtor/leads", response_model=List[LeadResponse])
def get_realtor_leads(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_realtor(user)
    leads = (
        db.query(Lead)
        .filter(Lead.assigned_realtor_id == user.id)
        .order_by(Lead.created_at.desc())
        .all()
    )
    return [_build_response(l, db) for l in leads]


@router.put("/realtor/leads/{lead_id}/status", status_code=204)
def realtor_update_lead_status(
    lead_id: str,
    body: StatusBody,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_realtor(user)
    allowed = {"contacted", "closed"}
    if body.status not in allowed:
        raise HTTPException(status_code=400, detail="Realtors can only set status to contacted or closed")
    lead = db.query(Lead).filter(Lead.id == UUID(lead_id)).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if str(lead.assigned_realtor_id) != str(user.id):
        raise HTTPException(status_code=403, detail="Not assigned to you")
    lead.status = body.status
    _apply_status_timestamp(lead, body.status)
    db.commit()


# ── Admin ─────────────────────────────────────────────────────────────────────

@router.get("/admin/leads", response_model=List[LeadResponse])
def admin_get_leads(
    type: Optional[str] = None,
    status: Optional[str] = None,
    assigned_realtor_id: Optional[str] = None,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(Lead)
    if type:
        q = q.filter(Lead.type == type)
    if status:
        q = q.filter(Lead.status == status)
    if assigned_realtor_id:
        q = q.filter(Lead.assigned_realtor_id == UUID(assigned_realtor_id))
    leads = q.order_by(Lead.created_at.desc()).all()
    return [_build_response(l, db) for l in leads]


@router.put("/admin/leads/{lead_id}/assign", status_code=204)
def admin_assign_lead(
    lead_id: str,
    body: AssignBody,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    lead = db.query(Lead).filter(Lead.id == UUID(lead_id)).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    realtor = db.query(User).filter(User.id == UUID(body.realtor_id), User.role == "realtor").first()
    if not realtor:
        raise HTTPException(status_code=404, detail="Realtor not found")
    lead.assigned_realtor_id = realtor.id
    lead.status = "assigned"
    _apply_status_timestamp(lead, "assigned")
    # Upgrade the submitting user to owner when their seller_interest lead is assigned
    owner_upgraded = None
    if lead.type == "seller_interest" and lead.from_user_id:
        owner = db.query(User).filter(User.id == lead.from_user_id).first()
        if owner and owner.role == "buyer":
            owner.role = "owner"
            owner_upgraded = owner
    db.commit()

    # Notify both parties after commit
    if owner_upgraded is not None:
        try:
            send_upgrade_approved_email(
                owner_upgraded.email,
                owner_upgraded.display_name or owner_upgraded.email,
                "owner",
            )
        except Exception:
            pass
        try:
            send_realtor_assigned_owner_email(
                realtor.email,
                realtor.display_name or realtor.email,
                owner_upgraded.display_name or owner_upgraded.email,
                owner_upgraded.email,
            )
        except Exception:
            pass


@router.put("/admin/leads/{lead_id}/status", status_code=204)
def admin_update_lead_status(
    lead_id: str,
    body: StatusBody,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    valid = {"new", "assigned", "contacted", "closed"}
    if body.status not in valid:
        raise HTTPException(status_code=400, detail=f"status must be one of {valid}")
    lead = db.query(Lead).filter(Lead.id == UUID(lead_id)).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.status = body.status
    _apply_status_timestamp(lead, body.status)
    db.commit()
