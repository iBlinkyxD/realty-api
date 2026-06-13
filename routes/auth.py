import hmac
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.user import User
from models.pending_user import PendingUser
from schemas.auth import RegisterRequest, RegisterResponse, LoginRequest, VerifyRequest, ResendCodeRequest, TokenResponse, GoogleAuthRequest, UpdateProfileRequest, ChangePasswordRequest, SetPasswordRequest
from utils.security import hash_password, verify_password
from utils.jwt import create_access_token, TOKEN_EXPIRE_HOURS
from utils.verification import generate_verification_code
from utils.email import send_verification_email, CODE_EXPIRE_MINUTES
from utils.auth import get_current_user
from utils.limiter import limiter
from utils.storage import upload_avatar

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

PENDING_USER_TTL_HOURS = 48


def _set_auth_cookie(response: Response, token: str) -> None:
    secure = settings.environment == "production"
    response.set_cookie(
        key="ildr_token",
        value=token,
        httponly=True,
        samesite="none" if secure else "lax",
        max_age=TOKEN_EXPIRE_HOURS * 3600,
        secure=secure,
        domain=settings.cookie_domain or None,
        path="/",
    )


@router.post("/register", response_model=RegisterResponse, status_code=201)
@limiter.limit("3/minute")
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    # Reject if already a verified user
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    code = generate_verification_code()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=PENDING_USER_TTL_HOURS)
    code_expires_at = datetime.now(timezone.utc) + timedelta(minutes=CODE_EXPIRE_MINUTES)
    now = datetime.now(timezone.utc)

    existing_pending = db.query(PendingUser).filter(PendingUser.email == body.email).first()

    if existing_pending:
        if existing_pending.last_code_sent_at:
            elapsed = (now - existing_pending.last_code_sent_at).total_seconds()
            if elapsed < RESEND_COOLDOWN_SECONDS:
                raise HTTPException(status_code=429, detail="Please wait before requesting another code")
        # Update existing pending row — fresh code, reset attempts, extend TTL
        existing_pending.password_hash = hash_password(body.password)
        existing_pending.display_name = body.display_name
        existing_pending.phone = body.phone
        existing_pending.verification_code = code
        existing_pending.verification_code_expires_at = code_expires_at
        existing_pending.verification_attempts = 0
        existing_pending.last_code_sent_at = now
        existing_pending.expires_at = expires_at
    else:
        pending = PendingUser(
            email=body.email,
            password_hash=hash_password(body.password),
            display_name=body.display_name,
            phone=body.phone,
            verification_code=code,
            verification_code_expires_at=code_expires_at,
            last_code_sent_at=now,
            expires_at=expires_at,
        )
        db.add(pending)

    db.commit()
    send_verification_email(body.email, code)
    return RegisterResponse(email=body.email)


MAX_VERIFY_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 60


@router.post("/verify", response_model=TokenResponse)
@limiter.limit("10/minute")
def verify_email(request: Request, body: VerifyRequest, response: Response, db: Session = Depends(get_db)):
    # Already verified and promoted to users table?
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already verified")

    pending = db.query(PendingUser).filter(PendingUser.email == body.email).first()
    if not pending:
        raise HTTPException(status_code=404, detail="Account not found")
    if pending.verification_attempts >= MAX_VERIFY_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many attempts — request a new code")
    if not pending.verification_code:
        raise HTTPException(status_code=400, detail="No verification code on file — request a new one")
    if pending.verification_code_expires_at and pending.verification_code_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Verification code has expired")
    if not hmac.compare_digest(pending.verification_code, body.code):
        pending.verification_attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid verification code")

    # Promote pending row → users table
    user = User(
        email=pending.email,
        password_hash=pending.password_hash,
        display_name=pending.display_name,
        phone=pending.phone,
        email_verified=True,
        # user_code is assigned by the DB sequence (DEFAULT nextval)
    )
    db.add(user)
    db.delete(pending)
    db.commit()
    db.refresh(user)

    token = create_access_token(user)
    _set_auth_cookie(response, token)
    return TokenResponse(expires_in=TOKEN_EXPIRE_HOURS * 3600)


@router.post("/resend-code", status_code=200)
@limiter.limit("5/minute")
def resend_code(request: Request, body: ResendCodeRequest, db: Session = Depends(get_db)):
    pending = db.query(PendingUser).filter(PendingUser.email == body.email).first()
    if not pending:
        # Either never registered, or already verified — return generic response
        return {"message": "If that email exists and is unverified, a new code has been sent"}

    now = datetime.now(timezone.utc)
    if pending.last_code_sent_at:
        elapsed = (now - pending.last_code_sent_at).total_seconds()
        if elapsed < RESEND_COOLDOWN_SECONDS:
            raise HTTPException(status_code=429, detail="Please wait before requesting another code")

    code = generate_verification_code()
    pending.verification_code = code
    pending.verification_code_expires_at = now + timedelta(minutes=CODE_EXPIRE_MINUTES)
    pending.verification_attempts = 0
    pending.last_code_sent_at = now
    db.commit()

    send_verification_email(pending.email, code)
    return {"message": "Verification code resent"}


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        # Give a helpful error if the account exists but is still pending verification
        if not user and db.query(PendingUser).filter(PendingUser.email == body.email).first():
            raise HTTPException(status_code=403, detail="Please verify your email before logging in")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.status == "suspended":
        raise HTTPException(status_code=403, detail="Account suspended")
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    token = create_access_token(user)
    _set_auth_cookie(response, token)
    return TokenResponse(expires_in=TOKEN_EXPIRE_HOURS * 3600)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "user_code": user.user_code,
        "email": user.email,
        "role": user.role,
        "display_name": user.display_name,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "has_password": user.password_hash is not None,
        "has_google": user.google_id is not None,
    }


AVATAR_ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
AVATAR_MAX_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("/avatar")
@limiter.limit("10/minute")
async def upload_user_avatar(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import filetype as ft
    data = await file.read()
    if len(data) > AVATAR_MAX_SIZE:
        raise HTTPException(status_code=413, detail="Avatar must be under 5 MB")
    detected = ft.guess(data[:2048])
    if detected is None or detected.mime not in AVATAR_ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, or WebP images are allowed")
    try:
        url = upload_avatar(data, detected.mime, str(user.id), user.avatar_url)
    except Exception:
        logger.exception("Avatar upload failed for user %s", user.id)
        raise HTTPException(status_code=500, detail="Avatar upload failed — please try again")
    user.avatar_url = url
    db.commit()
    return {"avatar_url": url}


@router.put("/me")
@limiter.limit("20/minute")
def update_profile(request: Request, body: UpdateProfileRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.display_name = body.display_name.strip()
    user.phone = body.phone.strip() if body.phone else None
    db.commit()
    db.refresh(user)
    return {"display_name": user.display_name, "phone": user.phone}


@router.put("/password")
@limiter.limit("5/minute")
def change_password(request: Request, body: ChangePasswordRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.password_hash:
        raise HTTPException(status_code=400, detail="This account uses Google sign-in — password change is not available")
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "Password updated"}


@router.post("/set-password", status_code=200)
@limiter.limit("5/minute")
def set_password(request: Request, body: SetPasswordRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.password_hash:
        raise HTTPException(status_code=400, detail="Account already has a password — use change password instead")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "Password set"}


@router.post("/link-google", status_code=200)
def link_google(body: GoogleAuthRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.google_id:
        raise HTTPException(status_code=400, detail="A Google account is already linked")

    req = urllib.request.Request(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {body.access_token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            info = json.loads(resp.read())
    except urllib.error.HTTPError:
        raise HTTPException(status_code=401, detail="Invalid Google token")
    except Exception:
        raise HTTPException(status_code=502, detail="Could not reach Google — try again")

    google_id = info.get("sub")
    if not google_id:
        raise HTTPException(status_code=401, detail="Google did not return required user info")
    if not info.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google account email is not verified")

    conflict = db.query(User).filter(User.google_id == google_id, User.id != user.id).first()
    if conflict:
        raise HTTPException(status_code=409, detail="This Google account is already linked to another user")

    user.google_id = google_id
    db.commit()
    return {"message": "Google account linked"}


@router.delete("/unlink-google", status_code=200)
def unlink_google(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.google_id:
        raise HTTPException(status_code=400, detail="No Google account linked")
    if not user.password_hash:
        raise HTTPException(status_code=400, detail="Set a password before unlinking Google so you can still sign in")
    user.google_id = None
    db.commit()
    return {"message": "Google account unlinked"}


@router.post("/google", response_model=TokenResponse)
def google_auth(body: GoogleAuthRequest, response: Response, db: Session = Depends(get_db)):
    req = urllib.request.Request(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {body.access_token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            info = json.loads(resp.read())
    except urllib.error.HTTPError:
        raise HTTPException(status_code=401, detail="Invalid Google token")
    except Exception:
        raise HTTPException(status_code=502, detail="Could not reach Google — try again")

    google_id = info.get("sub")
    email = info.get("email")
    name = (info.get("name") or (email.split("@")[0] if email else "User"))[:100]
    picture = info.get("picture")

    if not google_id or not email:
        raise HTTPException(status_code=401, detail="Google did not return required user info")
    if not info.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google account email is not verified")

    user = db.query(User).filter(User.google_id == google_id).first()

    if not user:
        user = db.query(User).filter(User.email == email).first()
        if user:
            # Existing password-registered account — link Google ID
            user.google_id = google_id
            if not user.avatar_url and picture:
                user.avatar_url = picture
            db.commit()
        else:
            # Brand-new Google sign-up — insert directly into users, bypassing pending_users
            # (Google already verified the email; user_code assigned by DB sequence)
            user = User(
                email=email,
                password_hash=None,
                display_name=name,
                google_id=google_id,
                email_verified=True,
                avatar_url=picture,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    elif picture and not user.avatar_url:
        user.avatar_url = picture
        db.commit()

    if user.status == "suspended":
        raise HTTPException(status_code=403, detail="Account suspended")

    token = create_access_token(user)
    _set_auth_cookie(response, token)
    return TokenResponse(expires_in=TOKEN_EXPIRE_HOURS * 3600)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(response: Response, user: User = Depends(get_current_user)):
    token = create_access_token(user)
    _set_auth_cookie(response, token)
    return TokenResponse(expires_in=TOKEN_EXPIRE_HOURS * 3600)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key="ildr_token",
        path="/",
        domain=settings.cookie_domain or None,
    )
    return {"message": "Logged out"}
