from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models.upgrade_request import UpgradeRequest
from schemas.upgrade_request import UpgradeRequestCreate, UpgradeRequestResponse
from utils.auth import get_current_user

router = APIRouter(prefix="/upgrade-requests", tags=["upgrade-requests"])


@router.post("", response_model=UpgradeRequestResponse, status_code=201)
def submit_upgrade_request(body: UpgradeRequestCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "buyer":
        raise HTTPException(status_code=403, detail="Only buyers can submit upgrade requests")

    if body.requested_role not in ("owner", "realtor"):
        raise HTTPException(status_code=422, detail="requested_role must be 'owner' or 'realtor'")

    existing = db.query(UpgradeRequest).filter(
        UpgradeRequest.user_id == user.id,
        UpgradeRequest.status == "pending",
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="You already have a pending upgrade request")

    req = UpgradeRequest(
        user_id=user.id,
        requested_role=body.requested_role,
        license_number=body.license_number,
        territory=body.territory,
        years_experience=body.years_experience,
        specialties=body.specialties,
        bio=body.bio,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.get("/me", response_model=List[UpgradeRequestResponse])
def get_my_upgrade_requests(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(UpgradeRequest).filter(
        UpgradeRequest.user_id == user.id
    ).all()
