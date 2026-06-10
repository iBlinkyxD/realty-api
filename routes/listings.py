from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models.listing import Listing
from models.user import User
from schemas.listing import ListingCreate, ListingUpdate, ListingResponse
from utils.auth import get_current_user
from utils.permission import require_role
from utils.storage import upload_image

router = APIRouter(prefix="/listings", tags=["listings"])


ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/heic"}
MAX_FILE_SIZE = 8 * 1024 * 1024  # 8 MB
MAX_FILES = 10


@router.post("/upload-images")
async def upload_images(
    files: List[UploadFile] = File(...),
    user=Depends(require_role("realtor")),
):
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_FILES} images allowed")

    urls: list[str] = []
    for f in files:
        if f.content_type not in ALLOWED_TYPES:
            raise HTTPException(status_code=415, detail=f"Unsupported file type: {f.content_type}")
        data = await f.read()
        if len(data) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"{f.filename} exceeds 8 MB limit")
        try:
            url = upload_image(data, f.content_type, str(user.id))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
        urls.append(url)

    return {"urls": urls}


@router.get("", response_model=List[ListingResponse])
def get_active_listings(db: Session = Depends(get_db)):
    return db.query(Listing).filter(Listing.status == "active").all()


@router.get("/mine", response_model=List[ListingResponse])
def get_my_listings(user=Depends(require_role("realtor")), db: Session = Depends(get_db)):
    return db.query(Listing).filter(Listing.submitted_by == user.id).all()


@router.post("", response_model=ListingResponse, status_code=201)
def create_listing(body: ListingCreate, user=Depends(require_role("realtor")), db: Session = Depends(get_db)):
    listing = Listing(
        **body.model_dump(),
        submitted_by=user.id,
        status="pending_approval",
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


@router.get("/{listing_id}", response_model=ListingResponse)
def get_listing(listing_id, db: Session = Depends(get_db)):
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


@router.put("/{listing_id}", response_model=ListingResponse)
def update_listing(listing_id, body: ListingUpdate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.submitted_by != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    was_rejected = listing.status == "rejected"
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(listing, field, value)
    if was_rejected:
        listing.status = "pending_approval"
        listing.rejection_reason = None
    db.commit()
    db.refresh(listing)
    return listing


@router.delete("/{listing_id}", status_code=204)
def archive_listing(listing_id, user=Depends(get_current_user), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.submitted_by != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    listing.status = "archived"
    db.commit()
