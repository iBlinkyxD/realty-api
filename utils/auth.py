from typing import Optional
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.user import User

_optional_bearer = HTTPBearer(auto_error=False)


def _decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_optional_bearer),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials if credentials else request.cookies.get("ildr_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = _decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="Email not verified")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="Account suspended")
    return user


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_optional_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    token = credentials.credentials if credentials else request.cookies.get("ildr_token")
    if not token:
        return None
    user_id = _decode_token(token)
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.email_verified or user.status != "active":
        return None
    return user
