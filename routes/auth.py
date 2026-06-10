import hmac
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.user import User
from schemas.auth import RegisterRequest, RegisterResponse, LoginRequest, VerifyRequest, ResendCodeRequest, TokenResponse
from utils.security import hash_password, verify_password
from utils.jwt import create_access_token, TOKEN_EXPIRE_HOURS
from utils.verification import generate_verification_code
from utils.email import send_verification_email, CODE_EXPIRE_MINUTES
from utils.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="ildr_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=TOKEN_EXPIRE_HOURS * 3600,
        secure=settings.environment == "production",
        domain=settings.cookie_domain or None,
        path="/",
    )


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    code = generate_verification_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=CODE_EXPIRE_MINUTES)

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        phone=body.phone,
        email_verified=False,
        verification_code=code,
        verification_code_expires_at=expires_at,
        last_code_sent_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()

    send_verification_email(body.email, code)

    return RegisterResponse(email=body.email)


MAX_VERIFY_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 60


@router.post("/verify", response_model=TokenResponse)
def verify_email(body: VerifyRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Account not found")
    if user.email_verified:
        raise HTTPException(status_code=400, detail="Email already verified")
    if user.verification_attempts >= MAX_VERIFY_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many attempts — request a new code")
    if not user.verification_code:
        raise HTTPException(status_code=400, detail="No verification code on file — request a new one")
    if not hmac.compare_digest(user.verification_code, body.code):
        user.verification_attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid verification code")
    if user.verification_code_expires_at and user.verification_code_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Verification code has expired")

    user.email_verified = True
    user.verification_code = None
    user.verification_code_expires_at = None
    user.verification_attempts = 0
    db.commit()
    db.refresh(user)

    token = create_access_token(user)
    _set_auth_cookie(response, token)
    return TokenResponse(access_token=token, expires_in=TOKEN_EXPIRE_HOURS * 3600)


@router.post("/resend-code", status_code=200)
def resend_code(body: ResendCodeRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or user.email_verified:
        return {"message": "If that email exists and is unverified, a new code has been sent"}

    now = datetime.now(timezone.utc)
    if user.last_code_sent_at:
        elapsed = (now - user.last_code_sent_at).total_seconds()
        if elapsed < RESEND_COOLDOWN_SECONDS:
            raise HTTPException(status_code=429, detail="Please wait before requesting another code")

    code = generate_verification_code()
    user.verification_code = code
    user.verification_code_expires_at = now + timedelta(minutes=CODE_EXPIRE_MINUTES)
    user.verification_attempts = 0
    user.last_code_sent_at = now
    db.commit()

    send_verification_email(user.email, code)
    return {"message": "Verification code resent"}


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.status == "suspended":
        raise HTTPException(status_code=403, detail="Account suspended")
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    token = create_access_token(user)
    _set_auth_cookie(response, token)
    return TokenResponse(access_token=token, expires_in=TOKEN_EXPIRE_HOURS * 3600)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "display_name": user.display_name,
    }


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key="ildr_token",
        path="/",
        domain=settings.cookie_domain or None,
    )
    return {"message": "Logged out"}
