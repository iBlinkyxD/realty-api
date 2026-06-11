from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import uuid


class RegisterRequest(BaseModel):
    display_name: str
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RegisterResponse(BaseModel):
    email: str
    message: str = "Verification code sent"


class VerifyRequest(BaseModel):
    email: EmailStr
    code: str


class ResendCodeRequest(BaseModel):
    email: EmailStr


class TokenResponse(BaseModel):
    expires_in: int = 3600
