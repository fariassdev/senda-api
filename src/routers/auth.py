"""
Authentication router for handling auth-related endpoints.

This module provides the REST API endpoints for authentication operations
including login, token refresh, and user session management.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from core.database import get_db
from core.auth import get_current_user_id
from services.auth_service import AuthenticationService
from repositories.user import UserRepository
from schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    TokenResponse,
)
from schemas.user import UserPublic

logger = logging.getLogger(__name__)

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/auth", tags=["authentication"])


def get_auth_service(db: Session = Depends(get_db)) -> AuthenticationService:
    return AuthenticationService(db)


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


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
            email_or_username=login_data.username, password=login_data.password
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


@router.get("/me", response_model=UserPublic)
async def get_current_user(
    current_user_id: str = Depends(get_current_user_id),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """
    Get Current User & Verify Session

    Validate JWT and return current admin user data.
    Requires JWT in Authorization: Bearer <token> header.
    """
    try:
        user = user_repo.get_user_by_id(current_user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user_repo.is_admin_user(user):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin privileges required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return UserPublic(
            id=user.id,
            email=user.email,
            username=user.username,
            name=user.name,
            role=user.role,
            last_login=user.last_login,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during user verification",
        )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")  # Rate limit: 10 refresh attempts per minute per IP
async def refresh_token(
    request: Request,
    token_data: RefreshTokenRequest,
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """
    Refresh Access Token

    Refresh JWT access token using a valid refresh token.
    Accepts refresh_token in request body and returns new access token.
    """
    client_ip = get_remote_address(request)
    logger.info(f"Token refresh attempt from IP: {client_ip}")

    try:
        token_response = auth_service.refresh_access_token(
            refresh_token=token_data.refresh_token
        )

        logger.info(f"Token refresh successful from IP: {client_ip}")
        return token_response

    except HTTPException as e:
        logger.warning(f"Token refresh failed from IP {client_ip}: {e.detail}")
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during token refresh from IP {client_ip}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during token refresh",
        )
