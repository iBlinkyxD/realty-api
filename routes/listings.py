import logging
import filetype
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func
from typing import List
from datetime import datetime, timezone
from uuid import UUID

logger = logging.getLogger(__name__)

from database import get_db
from models.listing import Listing
from models.listing_edit import ListingEdit
from models.listing_event import ListingEvent
from models.inquiry import Inquiry
from models.lead import Lead
from models.user import User
from models.deal_request import DealRequest
from schemas.listing import ListingCreate, ListingUpdate, ListingResponse
from schemas.deal_request import DealRequestCreate
from utils.auth import get_current_user
from utils.permission import require_role
from utils.storage import upload_image
from utils.limiter import limiter

router = APIRouter(prefix="/listings", tags=["listings"])


ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/heic"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
MAX_FILES = 25


@router.post("/upload-images")
@limiter.limit("20/minute")
async def upload_images(
    request: Request,
    files: List[UploadFile] = File(...),
    user=Depends(require_role("realtor", "admin")),
):
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_FILES} images allowed")

    urls: list[str] = []
    for f in files:
        data = await f.read()
        if len(data) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"{f.filename} exceeds 20 MB limit")
        detected = filetype.guess(data[:2048])
        if detected is None or detected.mime not in ALLOWED_TYPES:
            raise HTTPException(status_code=415, detail="Invalid file type")
        try:
            url = upload_image(data, detected.mime, str(user.id))
        except Exception:
            logger.exception("Image upload failed for user %s", user.id)
            raise HTTPException(status_code=500, detail="Image upload failed. Please try again.")
        urls.append(url)

    return {"urls": urls}


@router.get("", response_model=List[ListingResponse])
def get_active_listings(skip: int = 0, limit: int = Query(200, le=200), db: Session = Depends(get_db)):
    return db.query(Listing).filter(Listing.status == "active").order_by(Listing.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/mine", response_model=List[ListingResponse])
def get_my_listings(user=Depends(require_role("realtor", "owner")), db: Session = Depends(get_db)):
    from sqlalchemy import or_
    Submitter = aliased(User)
    leads_subq = (
        db.query(Lead.property_id, func.count(Lead.id).label("cnt"))
        .group_by(Lead.property_id)
        .subquery()
    )
    # Owners see listings where they are submitted_by (legacy) OR owner_id (new flow)
    if user.role == "owner":
        filter_cond = or_(Listing.submitted_by == user.id, Listing.owner_id == user.id)
    else:
        filter_cond = Listing.submitted_by == user.id
    rows = (
        db.query(Listing, leads_subq.c.cnt, Submitter)
        .outerjoin(leads_subq, leads_subq.c.property_id == Listing.id)
        .outerjoin(Submitter, Submitter.id == Listing.submitted_by)
        .filter(filter_cond)
        .all()
    )
    pending_deal_ids = {
        r.listing_id
        for r in db.query(DealRequest.listing_id)
        .filter(DealRequest.requested_by == user.id, DealRequest.status == "pending")
        .all()
    }
    pending_edit_ids = {
        r.listing_id
        for r in db.query(ListingEdit.listing_id)
        .filter(ListingEdit.submitted_by == user.id, ListingEdit.status == "pending")
        .all()
    }
    return [
        ListingResponse(
            **{c.key: getattr(l, c.key) for c in Listing.__table__.columns},
            leads_count=cnt or 0,
            has_pending_deal_request=l.id in pending_deal_ids,
            has_pending_edit=l.id in pending_edit_ids,
            submitted_by_name=submitter.display_name if submitter else None,
        )
        for l, cnt, submitter in rows
    ]


@router.get("/deal", response_model=List[ListingResponse])
def get_deal_listings(db: Session = Depends(get_db)):
    return db.query(Listing).filter(Listing.is_deal == True, Listing.status == "active").all()


@router.post("", response_model=ListingResponse, status_code=201)
def create_listing(body: ListingCreate, user=Depends(require_role("realtor", "admin")), db: Session = Depends(get_db)):
    listing = Listing(
        **body.model_dump(),
        submitted_by=user.id,
        status="active" if user.role == "admin" else "pending_approval",
    )
    db.add(listing)
    db.flush()  # get listing.id before commit
    db.add(ListingEvent(listing_id=listing.id, event_type="submitted", actor_id=user.id))
    db.commit()
    db.refresh(listing)
    return listing


@router.get("/{listing_id}", response_model=ListingResponse)
def get_listing(listing_id: UUID, db: Session = Depends(get_db)):
    row = (
        db.query(Listing, User)
        .join(User, User.id == Listing.submitted_by)
        .filter(Listing.id == listing_id, Listing.status == "active")
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing, submitter = row
    return ListingResponse(
        **{c.key: getattr(listing, c.key) for c in Listing.__table__.columns},
        submitted_by_name=submitter.display_name,
    )


@router.post("/{listing_id}/deal-request", status_code=201)
def submit_deal_request(
    listing_id: UUID,
    body: DealRequestCreate,
    user=Depends(require_role("realtor", "owner")),
    db: Session = Depends(get_db),
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.submitted_by != user.id:
        raise HTTPException(status_code=403, detail="Not your listing")
    if listing.status != "active":
        raise HTTPException(status_code=400, detail="Listing must be active to submit a deal request")
    if listing.is_deal:
        raise HTTPException(status_code=409, detail="Listing is already the deal of the week")
    existing = db.query(DealRequest).filter(
        DealRequest.listing_id == listing_id,
        DealRequest.requested_by == user.id,
        DealRequest.status == "pending",
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="You already have a pending deal request for this listing")
    db.add(DealRequest(
        listing_id=listing_id,
        requested_by=user.id,
        discount_value=body.discount_value,
        discount_type=body.discount_type,
        message=body.message,
    ))
    db.commit()
    return {"message": "Deal request submitted successfully"}


@router.post("/{listing_id}/view", status_code=204)
@limiter.limit("5/minute")
def record_view(request: Request, listing_id: UUID, db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id, Listing.status == "active").first()
    if listing:
        listing.view_count += 1
        db.commit()


@router.put("/{listing_id}", response_model=ListingResponse)
def update_listing(listing_id: UUID, body: ListingUpdate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.submitted_by != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Active listings edited by realtors go into a pending-edit queue instead of
    # updating in place so the live listing is not disrupted until admin approves.
    if listing.status == "active" and user.role != "admin":
        # Supersede any existing pending edit for this listing
        db.query(ListingEdit).filter(
            ListingEdit.listing_id == listing.id,
            ListingEdit.status == "pending",
        ).delete(synchronize_session=False)

        edit = ListingEdit(
            listing_id=listing.id,
            submitted_by=user.id,
            proposed_data=body.model_dump(mode='json'),
        )
        db.add(edit)
        db.add(ListingEvent(listing_id=listing.id, event_type="edit_submitted", actor_id=user.id))
        db.commit()
        db.refresh(listing)
        return listing

    was_rejected = listing.status == "rejected"
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(listing, field, value)
    if was_rejected:
        listing.status = "pending_approval"
        listing.rejection_reason = None
    listing.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(listing)
    return listing


@router.delete("/{listing_id}", status_code=204)
def archive_listing(listing_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.submitted_by != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    listing.status = "archived"
    db.commit()
