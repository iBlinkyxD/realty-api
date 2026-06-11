from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

from database import get_db
from models.inquiry import AnonymousLead
from utils.limiter import limiter

router = APIRouter(prefix="/leads", tags=["leads"])


class LeadCapture(BaseModel):
    name: str = Field(max_length=200)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=50)
    area: Optional[str] = Field(default=None, max_length=200)
    intent: Optional[str] = Field(default=None, max_length=200)


@router.post("/capture", status_code=201)
@limiter.limit("5/minute")
def capture_lead(request: Request, body: LeadCapture, db: Session = Depends(get_db)):
    lead = AnonymousLead(**body.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return {"id": str(lead.id), "status": "new"}
