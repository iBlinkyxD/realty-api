from datetime import datetime, timedelta, timezone
from jose import jwt
from config import settings
from models.user import User

TOKEN_EXPIRE_HOURS = 1


def create_access_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "email": user.email,
        "exp": exp,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
