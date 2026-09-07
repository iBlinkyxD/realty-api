from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.listing import Listing
from models.user import User

router = APIRouter(prefix="/stats", tags=["stats"])


class PlatformStats(BaseModel):
    active_listings: int
    total_value: float
    realtors: int
    registered_users: int


@router.get("/platform", response_model=PlatformStats)
def get_platform_stats(db: Session = Depends(get_db)):
    """Public counts backing the marketing stats on the homepage and auth
    screens — real numbers instead of hardcoded copy."""
    active_listings, total_value = (
        db.query(func.count(Listing.id), func.coalesce(func.sum(Listing.price), 0))
        .filter(Listing.status == "active")
        .one()
    )
    realtors = (
        db.query(func.count(User.id))
        .filter(User.role == "realtor", User.status == "active")
        .scalar()
    )
    registered_users = (
        db.query(func.count(User.id))
        .filter(User.role != "admin")
        .scalar()
    )

    return PlatformStats(
        active_listings=active_listings,
        total_value=float(total_value),
        realtors=realtors,
        registered_users=registered_users,
    )
