from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models.inquiry import Inquiry
from models.listing import Listing
from schemas.inquiry import InquiryCreate, InquiryResponse
from utils.auth import get_current_user, get_optional_user

router = APIRouter(prefix="/inquiries", tags=["inquiries"])


@router.post("", response_model=InquiryResponse, status_code=201)
def submit_inquiry(
    body: InquiryCreate,
    db: Session = Depends(get_db),
    user=Depends(get_optional_user),
):
    inquiry = Inquiry(
        listing_id=body.listing_id,
        name=body.name,
        email=body.email,
        phone=body.phone,
        message=body.message,
        from_user_id=user.id if user else None,
    )
    db.add(inquiry)
    db.commit()
    db.refresh(inquiry)

    listing_title = None
    if body.listing_id:
        listing = db.query(Listing).filter(Listing.id == body.listing_id).first()
        if listing:
            listing_title = listing.title

    return InquiryResponse(
        id=str(inquiry.id),
        listing_id=str(inquiry.listing_id) if inquiry.listing_id else None,
        listing_title=listing_title,
        name=inquiry.name,
        email=inquiry.email,
        phone=inquiry.phone,
        message=inquiry.message,
        created_at=inquiry.created_at,
    )


@router.get("/mine", response_model=List[InquiryResponse])
def get_my_inquiries(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Inquiry, Listing)
        .outerjoin(Listing, Listing.id == Inquiry.listing_id)
        .filter(Inquiry.from_user_id == user.id)
        .order_by(Inquiry.created_at.desc())
        .all()
    )
    return [
        InquiryResponse(
            id=str(inq.id),
            listing_id=str(inq.listing_id) if inq.listing_id else None,
            listing_title=listing.title if listing else None,
            name=inq.name,
            email=inq.email,
            phone=inq.phone,
            message=inq.message,
            created_at=inq.created_at,
        )
        for inq, listing in rows
    ]
