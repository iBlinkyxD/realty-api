from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from database import get_db
from models.booking import Booking
from models.lead import Lead
from models.listing import Listing
from models.user import User
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

    duplicate = db.query(Booking).filter(
        Booking.buyer_id == user.id,
        Booking.listing_id == body.listing_id,
        Booking.status != "cancelled",
        Booking.check_in < body.check_out,
        Booking.check_out > body.check_in,
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="You already have a booking for this listing on overlapping dates")

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

    # Create a lead so admin can assign a realtor to follow up
    lead = Lead(
        type="booking",
        name=user.display_name or user.email.split("@")[0],
        email=user.email,
        property_id=body.listing_id,
        from_user_id=user.id,
        message=f"Check-in: {body.check_in}, Check-out: {body.check_out}, Guests: {body.guests}" + (f"\nNotes: {body.notes}" if body.notes else ""),
        status="new",
    )
    db.add(lead)

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


@router.put("/{booking_id}/cancel", status_code=204)
def cancel_booking(booking_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id, Booking.buyer_id == user.id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status not in ("pending", "confirmed"):
        raise HTTPException(status_code=400, detail="Only pending or confirmed bookings can be cancelled")
    booking.status = "cancelled"
    db.commit()


@router.put("/{booking_id}/accept", status_code=204)
def accept_booking(booking_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.query(Booking, Listing).join(Listing, Listing.id == Booking.listing_id).filter(
        Booking.id == booking_id, Listing.submitted_by == user.id
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    b, _ = booking
    if b.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending bookings can be accepted")
    b.status = "confirmed"
    db.commit()


@router.put("/{booking_id}/decline", status_code=204)
def decline_booking(booking_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.query(Booking, Listing).join(Listing, Listing.id == Booking.listing_id).filter(
        Booking.id == booking_id, Listing.submitted_by == user.id
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    b, _ = booking
    if b.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending bookings can be declined")
    b.status = "cancelled"
    db.commit()


@router.get("/for-owner", response_model=List[BookingResponse])
def get_bookings_for_owner(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Booking, Listing, User)
        .join(Listing, Listing.id == Booking.listing_id)
        .join(User, User.id == Booking.buyer_id)
        .filter(Listing.submitted_by == user.id)
        .order_by(Booking.check_in.asc())
        .all()
    )
    return [
        BookingResponse(
            id=str(b.id),
            listing_id=str(b.listing_id),
            listing_title=listing.title,
            listing_location=listing.location,
            listing_images=listing.images or [],
            check_in=str(b.check_in),
            check_out=str(b.check_out),
            guests=b.guests,
            total_price=float(b.total_price) if b.total_price else None,
            notes=b.notes,
            status=b.status,
            created_at=b.created_at,
            guest_name=guest.display_name,
        )
        for b, listing, guest in rows
    ]
