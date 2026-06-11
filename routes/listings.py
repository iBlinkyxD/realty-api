import logging
import filetype
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime, timezone
from uuid import UUID

logger = logging.getLogger(__name__)

from database import get_db
from models.listing import Listing
from models.listing_edit import ListingEdit
from models.inquiry import Inquiry
from models.user import User
from schemas.listing import ListingCreate, ListingUpdate, ListingResponse
from utils.auth import get_current_user
from utils.permission import require_role
from utils.storage import upload_image

router = APIRouter(prefix="/listings", tags=["listings"])


ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/heic"}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB
MAX_FILES = 25


@router.post("/upload-images")
async def upload_images(
    files: List[UploadFile] = File(...),
    user=Depends(require_role("realtor", "admin")),
):
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_FILES} images allowed")

    urls: list[str] = []
    for f in files:
        data = await f.read()
        if len(data) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"{f.filename} exceeds 25 MB limit")
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
def get_active_listings(db: Session = Depends(get_db)):
    return db.query(Listing).filter(Listing.status == "active").all()


@router.get("/mine", response_model=List[ListingResponse])
def get_my_listings(user=Depends(require_role("realtor")), db: Session = Depends(get_db)):
    leads_subq = (
        db.query(Inquiry.listing_id, func.count(Inquiry.id).label("cnt"))
        .group_by(Inquiry.listing_id)
        .subquery()
    )
    rows = (
        db.query(Listing, leads_subq.c.cnt)
        .outerjoin(leads_subq, leads_subq.c.listing_id == Listing.id)
        .filter(Listing.submitted_by == user.id)
        .all()
    )
    return [
        ListingResponse(
            **{c.key: getattr(l, c.key) for c in Listing.__table__.columns},
            leads_count=cnt or 0,
        )
        for l, cnt in rows
    ]


@router.post("", response_model=ListingResponse, status_code=201)
def create_listing(body: ListingCreate, user=Depends(require_role("realtor", "admin")), db: Session = Depends(get_db)):
    listing = Listing(
        **body.model_dump(),
        submitted_by=user.id,
        status="active" if user.role == "admin" else "pending_approval",
    )
    db.add(listing)
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
        submitted_by_email=submitter.email,
    )


@router.post("/{listing_id}/view", status_code=204)
def record_view(listing_id: UUID, db: Session = Depends(get_db)):
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
