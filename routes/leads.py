from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database import get_db
from models.inquiry import AnonymousLead

router = APIRouter(prefix="/leads", tags=["leads"])


class LeadCapture(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    area: Optional[str] = None
    intent: Optional[str] = None


@router.post("/capture", status_code=201)
def capture_lead(body: LeadCapture, db: Session = Depends(get_db)):
    lead = AnonymousLead(**body.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return {"id": str(lead.id), "status": "new"}
