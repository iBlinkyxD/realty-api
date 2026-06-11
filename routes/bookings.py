from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models.booking import Booking
from models.listing import Listing
from schemas.booking import BookingCreate, BookingResponse
from utils.auth import get_current_user

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingResponse, status_code=201)
def create_booking(
    body: BookingCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing = db.query(Listing).filter(Listing.id == body.listing_id, Listing.status == "active").first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.transaction != "rent":
        raise HTTPException(status_code=400, detail="Bookings are only for rental listings")

    booking = Booking(
        listing_id=body.listing_id,
        buyer_id=user.id,
        check_in=body.check_in,
        check_out=body.check_out,
        guests=body.guests,
        notes=body.notes,
        status="pending",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    return BookingResponse(
        id=str(booking.id),
        listing_id=str(booking.listing_id),
        listing_title=listing.title,
        listing_location=listing.location,
        listing_images=listing.images or [],
        check_in=booking.check_in,
        check_out=booking.check_out,
        guests=booking.guests,
        total_price=float(booking.total_price) if booking.total_price else None,
        notes=booking.notes,
        status=booking.status,
        created_at=booking.created_at,
    )


@router.get("/mine", response_model=List[BookingResponse])
def get_my_bookings(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Booking, Listing)
        .join(Listing, Listing.id == Booking.listing_id)
        .filter(Booking.buyer_id == user.id)
        .order_by(Booking.created_at.desc())
        .all()
    )
    return [
        BookingResponse(
            id=str(b.id),
            listing_id=str(b.listing_id),
            listing_title=listing.title,
            listing_location=listing.location,
            listing_images=listing.images or [],
            check_in=b.check_in,
            check_out=b.check_out,
            guests=b.guests,
            total_price=float(b.total_price) if b.total_price else None,
            notes=b.notes,
            status=b.status,
            created_at=b.created_at,
        )
        for b, listing in rows
    ]
