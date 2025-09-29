from pydantic import BaseModel, Field
from typing import Literal

from src.senda.api.schemas.user import UserPublic


class LoginRequest(BaseModel):
    """Schema for login requests."""

    email_or_username: str = Field(..., description="Email address or username")
    password: str


class LoginResponse(BaseModel):
    """Schema for successful login responses."""

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int  # seconds
    user: UserPublic


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token requests."""

    refresh_token: str


class TokenResponse(BaseModel):
    """Schema for token refresh responses."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int  # seconds
