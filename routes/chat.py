from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models.listing import Listing
from config import settings
from utils.limiter import limiter

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/chat/listings")
@limiter.limit("30/minute")
def chat_listings(
    request: Request,
    location: Optional[str] = Query(None, description="Region or city — e.g. 'Punta Cana'"),
    transaction: Optional[str] = Query(None, description="sale | rent"),
    type: Optional[str] = Query(None, description="villa | apartment | condo | land | commercial"),
    bedrooms: Optional[int] = Query(None, ge=1, description="Minimum bedrooms"),
    min_price: Optional[float] = Query(None, ge=0, description="Min price USD"),
    max_price: Optional[float] = Query(None, ge=0, description="Max price USD"),
    min_roi: Optional[float] = Query(None, ge=0, description="Min ROI percentage"),
    seller_financing: Optional[bool] = Query(None),
    tax_exempt: Optional[bool] = Query(None),
    gated_community: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Listing).filter(Listing.status == "active")

    if location:
        query = query.filter(Listing.location.ilike(f"%{location}%"))
    if transaction in ("sale", "rent"):
        query = query.filter(
            (Listing.transaction == transaction) | (Listing.transaction == "both")
        )
    if type in ("villa", "apartment", "condo", "land", "commercial"):
        query = query.filter(Listing.type == type)
    if bedrooms:
        query = query.filter(Listing.bedrooms >= bedrooms)
    if min_price is not None:
        query = query.filter(Listing.price >= min_price)
    if max_price is not None:
        query = query.filter(Listing.price <= max_price)
    if min_roi is not None:
        query = query.filter(Listing.roi >= min_roi)
    if seller_financing is True:
        query = query.filter(Listing.seller_financing.is_(True))
    if tax_exempt is True:
        query = query.filter(Listing.tax_exempt.is_(True))
    if gated_community is True:
        query = query.filter(Listing.gated_community.is_(True))

    listings = query.order_by(Listing.created_at.desc()).limit(5).all()

    base_url = settings.landing_url.rstrip("/")

    # Build filter summary for messages
    filter_parts = []
    if location:
        filter_parts.append(f"in {location}")
    if transaction:
        filter_parts.append(f"for {transaction}")
    if type:
        filter_parts.append(f"({type})")
    if bedrooms:
        filter_parts.append(f"{bedrooms}+ bedrooms")
    if max_price:
        filter_parts.append(f"under ${max_price:,.0f}")
    if min_roi:
        filter_parts.append(f"{min_roi:.0f}%+ ROI")
    filter_str = " ".join(filter_parts)

    if not listings:
        message = (
            f"I couldn't find any active listings{' ' + filter_str if filter_str else ''} right now.\n\n"
            f"Browse everything available here: {base_url}/search\n\n"
            "Or talk to one of our agents and they'll shortlist options matching your goals within 24 hours."
        )
        return {"message": message, "count": 0, "has_results": False}

    # Format each listing
    cards = []
    for i, l in enumerate(listings, 1):
        price = f"${float(l.price):,.0f}" if l.price else "Price on request"
        url = f"{base_url}/listing/{l.id}"

        specs = []
        if l.bedrooms:
            specs.append(f"{l.bedrooms} bd")
        if l.bathrooms:
            specs.append(f"{int(l.bathrooms)} ba")
        if l.area_sqft:
            specs.append(f"{l.area_sqft:,} m²")
        spec_str = " · ".join(specs)

        perks = []
        if l.roi:
            perks.append(f"📈 {float(l.roi):.0f}% ROI")
        if l.is_deal:
            perks.append("🔥 Deal of the week")
        if l.seller_financing:
            perks.append("💳 Seller financing")
        if l.tax_exempt:
            perks.append("🏛️ CONFOTUR tax exempt")
        if l.gated_community:
            perks.append("🔒 Gated community")
        perk_str = "  ".join(perks)

        entry = f"{i}. {l.title}\n"
        entry += f"   📍 {l.location}  |  {price}"
        if spec_str:
            entry += f"  |  {spec_str}"
        if perk_str:
            entry += f"\n   {perk_str}"
        entry += f"\n   🔗 {url}"

        cards.append(entry)

    count = len(listings)
    header = f"Here {'is' if count == 1 else 'are'} {count} propert{'y' if count == 1 else 'ies'}"
    if filter_str:
        header += f" {filter_str}"
    header += ":"

    footer = f"\n🔍 Browse all listings: {base_url}/search"

    message = header + "\n\n" + "\n\n".join(cards) + "\n" + footer

    return {"message": message, "count": count, "has_results": True}
