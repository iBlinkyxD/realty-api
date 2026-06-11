from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models.saved_home import SavedHome
from models.listing import Listing
from schemas.saved_home import SavedHomeResponse
from utils.auth import get_current_user

router = APIRouter(prefix="/saved-homes", tags=["saved-homes"])


@router.get("/mine", response_model=List[SavedHomeResponse])
def get_saved_homes(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(SavedHome, Listing)
        .join(Listing, Listing.id == SavedHome.listing_id)
        .filter(SavedHome.user_id == user.id)
        .order_by(SavedHome.created_at.desc())
        .all()
    )
    return [
        SavedHomeResponse(
            id=str(saved.id),
            listing_id=str(saved.listing_id),
            listing_title=listing.title,
            listing_location=listing.location,
            listing_price=float(listing.price),
            listing_transaction=listing.transaction,
            listing_images=listing.images or [],
            listing_bedrooms=listing.bedrooms,
            listing_bathrooms=listing.bathrooms,
            saved_at=saved.created_at,
        )
        for saved, listing in rows
    ]


@router.post("/{listing_id}", status_code=201)
def save_home(listing_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    existing = db.query(SavedHome).filter(
        SavedHome.user_id == user.id,
        SavedHome.listing_id == listing_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Already saved")

    db.add(SavedHome(user_id=user.id, listing_id=listing_id))
    db.commit()
    return {"status": "saved"}


@router.delete("/{listing_id}", status_code=204)
def unsave_home(listing_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    saved = db.query(SavedHome).filter(
        SavedHome.user_id == user.id,
        SavedHome.listing_id == listing_id,
    ).first()
    if not saved:
        raise HTTPException(status_code=404, detail="Not saved")
    db.delete(saved)
    db.commit()
