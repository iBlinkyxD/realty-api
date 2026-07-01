import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from config import settings
from database import get_db
from models.booking import Booking
from models.lead import Lead
from models.listing import Listing
from models.user import User
from schemas.booking import BookingCreate, BookingResponse
from utils.auth import get_current_user, get_optional_user
from utils import ghl
from utils.email import send_lead_notification
from models.site_settings import SiteSettings

_DATE_RANGE_RE = re.compile(r"Check-in: (\d{4}-\d{2}-\d{2}), Check-out: (\d{4}-\d{2}-\d{2})")

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get("/unavailable/{listing_id}")
def get_unavailable_dates(listing_id: UUID, db: Session = Depends(get_db)):
    """Public — returns check-in/check-out ranges for closed booking leads on a listing."""
    leads = (
        db.query(Lead)
        .filter(Lead.type == "booking", Lead.property_id == listing_id, Lead.status == "closed")
        .all()
    )
    ranges = []
    for lead in leads:
        if lead.message:
            m = _DATE_RANGE_RE.search(lead.message)
            if m:
                ranges.append({"check_in": m.group(1), "check_out": m.group(2)})
    return ranges


def _notify_email(db: Session) -> str:
    row = db.query(SiteSettings).filter(SiteSettings.id == 1).first()
    if row and row.data and row.data.get("notify_email"):
        return row.data["notify_email"]
    return settings.notify_email


@router.post("", response_model=BookingResponse, status_code=201)
def create_booking(
    body: BookingCreate,
    user=Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    listing = db.query(Listing).filter(Listing.id == body.listing_id, Listing.status == "active").first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.transaction != "rent":
        raise HTTPException(status_code=400, detail="Bookings are only for rental listings")

    # Resolve contact info — use account data for logged-in users, body fields for guests
    if user:
        guest_name = user.display_name or user.email.split("@")[0]
        guest_email = user.email
        guest_phone = getattr(user, "phone", None)
    else:
        guest_name = (body.name or "").strip() or None
        guest_email = body.email
        guest_phone = body.phone
        if not guest_name or not guest_email:
            raise HTTPException(status_code=422, detail="name and email are required for guest bookings")

    message = f"Check-in: {body.check_in}, Check-out: {body.check_out}, Guests: {body.guests}"
    if body.notes:
        message += f"\nNotes: {body.notes}"

    lead = Lead(
        type="booking",
        name=guest_name,
        email=guest_email,
        phone=guest_phone,
        property_id=body.listing_id,
        from_user_id=user.id if user else None,
        message=message,
        status="new",
    )
    db.add(lead)

    booking = None
    if user:
        duplicate = db.query(Booking).filter(
            Booking.buyer_id == user.id,
            Booking.listing_id == body.listing_id,
            Booking.status != "cancelled",
            Booking.check_in < str(body.check_out),
            Booking.check_out > str(body.check_in),
        ).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="You already have a booking for this listing on overlapping dates")

        booking = Booking(
            listing_id=body.listing_id,
            buyer_id=user.id,
            check_in=str(body.check_in),
            check_out=str(body.check_out),
            guests=body.guests,
            notes=body.notes,
            status="pending",
        )
        db.add(booking)

    db.commit()
    db.refresh(lead)
    if booking:
        db.refresh(booking)

    property_info = {
        "id": str(listing.id),
        "title": listing.title,
        "price": float(listing.price) if listing.price else None,
        "location": listing.location,
        "bedrooms": listing.bedrooms,
        "bathrooms": float(listing.bathrooms) if listing.bathrooms else None,
        "listing_type": listing.type,
    }
    ghl.create_contact(lead, property_info, db)
    try:
        send_lead_notification(lead, property_info, notify_email=_notify_email(db))
    except Exception:
        pass

    if booking:
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

    return BookingResponse(
        id=str(lead.id),
        listing_id=str(listing.id),
        listing_title=listing.title,
        listing_location=listing.location,
        listing_images=listing.images or [],
        check_in=str(body.check_in),
        check_out=str(body.check_out),
        guests=body.guests,
        total_price=None,
        notes=body.notes,
        status="pending",
        created_at=lead.created_at,
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
