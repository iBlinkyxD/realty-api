import logging
import filetype
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from sqlalchemy.orm import Session, aliased
from sqlalchemy import and_, func, or_
from typing import List, Optional
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
from schemas.listing import ListingCreate, ListingUpdate, ListingResponse, ListingPageResponse
from schemas.deal_request import DealRequestCreate
from utils.auth import get_current_user
from utils.permission import require_role
from utils.storage import upload_image
from utils.share_image import generate_share_image, maybe_regenerate_share_image
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


SORT_COLUMNS = {
    "new":  lambda: Listing.created_at.desc(),
    "low":  lambda: Listing.price.asc(),
    "high": lambda: Listing.price.desc(),
    "roi":  lambda: Listing.roi.desc(),
}


def _apply_listing_filters(
    query,
    purpose: Optional[str] = None,
    type: Optional[str] = None,
    region: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    beds: Optional[int] = None,
    min_roi: Optional[float] = None,
    features: Optional[List[str]] = None,
):
    """Shared by the item query, the total count, and the aggregate (median/avg)
    queries so they can never drift out of sync with each other."""
    query = query.filter(Listing.status == "active")
    if purpose == "rent":
        query = query.filter(Listing.transaction == "rent")
    elif purpose == "investment":
        query = query.filter(Listing.roi >= 7)
    if type and type != "All":
        query = query.filter(Listing.type == type.lower())
    if region:
        query = query.filter(Listing.location.ilike(f"%{region}%"))
    if beds is not None:
        query = query.filter(Listing.bedrooms >= beds)
    if min_roi:
        query = query.filter(Listing.roi >= min_roi)
    # Rent listings are exempt from the sale price filter, regardless of purpose.
    price_conditions = [Listing.price >= (min_price or 0)]
    if max_price is not None:
        price_conditions.append(Listing.price <= max_price)
    query = query.filter(or_(Listing.transaction == "rent", and_(*price_conditions)))
    if features:
        query = query.filter(Listing.features.op("@>")(features))
    return query


@router.get("", response_model=ListingPageResponse)
def get_active_listings(
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=60),
    purpose: Optional[str] = Query(None, description="rent | investment (omit for sale/all)"),
    type: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    beds: Optional[int] = Query(None, ge=0),
    min_roi: Optional[float] = Query(None, ge=0),
    features: Optional[List[str]] = Query(None),
    sort: str = Query("new"),
    exclude_ids: Optional[List[UUID]] = Query(None),
    include_aggregates: bool = Query(True),
    db: Session = Depends(get_db),
):
    base = _apply_listing_filters(
        db.query(Listing), purpose=purpose, type=type, region=region,
        min_price=min_price, max_price=max_price, beds=beds, min_roi=min_roi, features=features,
    )
    if exclude_ids:
        base = base.filter(~Listing.id.in_(exclude_ids))

    total = base.with_entities(func.count(Listing.id)).scalar() or 0

    order_by = SORT_COLUMNS.get(sort, SORT_COLUMNS["new"])()
    items = base.order_by(order_by).offset((page - 1) * page_size).limit(page_size).all()

    median_price = None
    avg_roi = None
    if include_aggregates:
        sale_base = base.filter(Listing.transaction != "rent")
        median_price = sale_base.with_entities(
            func.percentile_cont(0.5).within_group(Listing.price.asc())
        ).scalar()
        avg_roi = base.filter(Listing.roi > 0).with_entities(func.avg(Listing.roi)).scalar()

    return ListingPageResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        median_price=float(median_price) if median_price is not None else None,
        avg_roi=float(avg_roi) if avg_roi is not None else None,
    )


def _my_listings_base_query(db: Session, user):
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
        filter_cond = or_(Listing.submitted_by == user.id, Listing.assigned_realtor_id == user.id)
    return (
        db.query(Listing, leads_subq.c.cnt, Submitter)
        .outerjoin(leads_subq, leads_subq.c.property_id == Listing.id)
        .outerjoin(Submitter, Submitter.id == Listing.submitted_by)
        .filter(filter_cond)
    )


def _my_listings_pending_sets(db: Session, user):
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
    return pending_deal_ids, pending_edit_ids


def _to_my_listing_response(row, pending_deal_ids, pending_edit_ids) -> ListingResponse:
    l, cnt, submitter = row
    return ListingResponse(
        **{c.key: getattr(l, c.key) for c in Listing.__table__.columns},
        leads_count=cnt or 0,
        has_pending_deal_request=l.id in pending_deal_ids,
        has_pending_edit=l.id in pending_edit_ids,
        submitted_by_name=submitter.display_name if submitter else None,
    )


@router.get("/mine", response_model=List[ListingResponse])
def get_my_listings(user=Depends(require_role("realtor", "owner")), db: Session = Depends(get_db)):
    rows = _my_listings_base_query(db, user).all()
    pending_deal_ids, pending_edit_ids = _my_listings_pending_sets(db, user)
    return [_to_my_listing_response(row, pending_deal_ids, pending_edit_ids) for row in rows]


@router.get("/mine/page", response_model=ListingPageResponse)
def get_my_listings_page(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    pending_review: Optional[bool] = Query(None, description="Only listings with a pending deal request or edit"),
    user=Depends(require_role("realtor", "owner")),
    db: Session = Depends(get_db),
):
    """Paginated/filtered variant of GET /mine, used by the realtor/owner "My
    Listings" tables. GET /mine itself stays unparameterized and unpaginated —
    the home-dashboard widgets rely on it returning the complete list."""
    query = _my_listings_base_query(db, user)
    if status:
        query = query.filter(Listing.status == status)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Listing.title.ilike(like), Listing.location.ilike(like)))

    pending_deal_ids, pending_edit_ids = _my_listings_pending_sets(db, user)
    if pending_review:
        review_ids = pending_deal_ids | pending_edit_ids
        if not review_ids:
            return ListingPageResponse(items=[], total=0, page=page, page_size=page_size)
        query = query.filter(Listing.id.in_(review_ids))

    total = query.with_entities(func.count(Listing.id)).scalar() or 0
    rows = query.order_by(Listing.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [_to_my_listing_response(row, pending_deal_ids, pending_edit_ids) for row in rows]
    return ListingPageResponse(items=items, total=total, page=page, page_size=page_size)


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
    try:
        listing.share_image_url = generate_share_image(listing)
    except Exception:
        logger.exception("Share image generation failed for listing %s", listing.id)
    db.commit()
    db.refresh(listing)
    return listing


@router.get("/{listing_id}", response_model=ListingResponse)
def get_listing(listing_id: UUID, db: Session = Depends(get_db)):
    AssignedRealtor = aliased(User)
    row = (
        db.query(Listing, User, AssignedRealtor)
        .join(User, User.id == Listing.submitted_by)
        .outerjoin(AssignedRealtor, AssignedRealtor.id == Listing.assigned_realtor_id)
        .filter(Listing.id == listing_id, Listing.status == "active")
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing, submitter, assigned_realtor = row
    # The assigned realtor (if any) takes over as the public "Listed by" contact.
    contact = assigned_realtor or submitter
    return ListingResponse(
        **{c.key: getattr(listing, c.key) for c in Listing.__table__.columns},
        submitted_by_name=contact.display_name,
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
    if listing.submitted_by != user.id and listing.assigned_realtor_id != user.id:
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

    if listing.submitted_by != user.id and listing.assigned_realtor_id != user.id and user.role != "admin":
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
            proposed_data=body.model_dump(exclude_unset=True, mode='json'),
        )
        db.add(edit)
        db.add(ListingEvent(listing_id=listing.id, event_type="edit_submitted", actor_id=user.id))
        db.commit()
        db.refresh(listing)
        return listing

    was_rejected = listing.status == "rejected"
    changed = body.model_dump(exclude_none=True)
    for field, value in changed.items():
        setattr(listing, field, value)
    if was_rejected:
        listing.status = "pending_approval"
        listing.rejection_reason = None
    listing.updated_at = datetime.now(timezone.utc)
    maybe_regenerate_share_image(listing, changed.keys())
    db.commit()
    db.refresh(listing)
    return listing


@router.delete("/{listing_id}", status_code=204)
def archive_listing(listing_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.submitted_by != user.id and listing.assigned_realtor_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    listing.status = "archived"
    db.commit()
