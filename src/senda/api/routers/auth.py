"""
Authentication router for handling auth-related endpoints.

This module provides the REST API endpoints for authentication operations
including login, token refresh, and user session management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request

from src.senda.api.core.database import get_db
from src.senda.api.services.auth_service import AuthenticationService
from src.senda.api.schemas.auth import LoginRequest, LoginResponse

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/auth", tags=["authentication"])

# Add rate limit exception handler
router.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def get_auth_service(db: Session = Depends(get_db)) -> AuthenticationService:
    return AuthenticationService(db)


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")  # Rate limit: 5 attempts per minute per IP
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """
    Admin Login Endpoint

    Authenticate admin user with email/username and password. Returns JWT and user data.

    """
    try:
        # The OAuth2PasswordRequestForm provides username and password
        # We'll use username field for email_or_username (more flexible)
        login_response = auth_service.login(
            email_or_username=form_data.username, password=form_data.password
        )

        return login_response

    except HTTPException:
        # Re-raise HTTP exceptions from the service
        raise
    except Exception:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication",
        )


@router.post("/login-json", response_model=LoginResponse)
@limiter.limit("5/minute")  # Rate limit: 5 attempts per minute per IP
async def login_json(
    request: Request,
    login_data: LoginRequest,
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """
    Alternative JSON-based login endpoint (for non-OAuth2 compatible clients).

    Same functionality as `/login` but accepts JSON payload instead of form data.
    """
    try:
        login_response = auth_service.login(
            email_or_username=login_data.email_or_username, password=login_data.password
        )

        return login_response

    except HTTPException:
        # Re-raise HTTP exceptions from the service
        raise
    except Exception:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication",
        )
