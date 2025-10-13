"""
Authentication service for handling login and user authentication logic.

This module provides the business logic layer for authentication operations
including login validation, token generation, and security checks.
"""

import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models.user import User
from repositories.user import UserRepository
from core.auth import (
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    hash_refresh_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from schemas.auth import LoginResponse, TokenResponse
from schemas.user import UserPublic


logger = logging.getLogger(__name__)


class AuthenticationService:
    """Service for authentication operations."""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def _safely_revoke_refresh_token(self, stored_token, reason: str) -> None:
        """
        Safely revoke a refresh token with error handling and logging.

        Args:
            stored_token: The RefreshToken instance to revoke
            reason: Reason for revocation (for logging)
        """
        if stored_token:
            try:
                self.user_repo.revoke_refresh_token(stored_token)
                logger.info(f"Refresh token revoked due to {reason}")
            except Exception as revoke_error:
                logger.error(f"Failed to revoke token during {reason}: {revoke_error}")

    def authenticate_user(
        self, email_or_username: str, password: str
    ) -> Tuple[bool, Optional[User], str]:
        """
        Authenticate user with email/username and password.

        Args:
            email_or_username: Email address or username
            password: Plain text password

        Returns:
            Tuple of (success, user, error_message)
        """
        # Get user by email or username
        user = self.user_repo.get_user_by_email_or_username(email_or_username)
        if not user:
            return False, None, "Invalid credentials"

        # Check if account is locked
        if self.user_repo.is_account_locked(user):
            return (
                False,
                None,
                "Account is temporarily locked due to failed login attempts",
            )

        # Verify password
        if not verify_password(password, user.password_hash):
            # Increment failed attempts
            self.user_repo.increment_failed_login_attempts(user)
            return False, None, "Invalid credentials"

        # Check if user is admin
        if not self.user_repo.is_admin_user(user):
            return False, None, "Access denied: Admin privileges required"

        # Reset failed attempts on successful login
        self.user_repo.reset_failed_login_attempts(user)

        return True, user, ""

    def login(self, email_or_username: str, password: str) -> LoginResponse:
        """
        Login user and return JWT tokens.

        Args:
            email_or_username: Email address or username
            password: Plain text password

        Returns:
            LoginResponse with tokens and user data

        Raises:
            HTTPException: If authentication fails
        """
        success, user, error_message = self.authenticate_user(
            email_or_username, password
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_message,
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create access token
        access_token = create_access_token(
            data={"sub": str(user.id), "username": user.username, "role": user.role}
        )

        # Create refresh token
        refresh_token = create_refresh_token(
            data={"sub": str(user.id), "username": user.username}
        )

        # Store refresh token hash in database
        refresh_token_hash = hash_refresh_token(refresh_token)
        self.user_repo.store_refresh_token(user, refresh_token_hash)

        # Convert user to public schema
        user_public = UserPublic(
            id=user.id,
            email=user.email,
            username=user.username,
            name=user.name,
            role=user.role,
            last_login=user.last_login,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
            user=user_public,
        )

    def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """
        Refresh access token using a valid refresh token with token rotation.

        Implements secure token rotation: the provided refresh token is revoked
        and a new refresh token is issued along with the new access token.

        Args:
            refresh_token: The refresh token

        Returns:
            TokenResponse with new access token and new refresh token

        Raises:
            HTTPException: If refresh token is invalid or expired
        """
        stored_token = None
        try:
            # Verify the refresh token JWT
            payload = verify_token(refresh_token, expected_type="refresh")
            user_id = payload.get("sub")

            if not user_id:
                logger.warning("Refresh token attempt with missing user ID")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token: missing user ID",
                )

            # Hash the token to look it up in the database
            token_hash = hash_refresh_token(refresh_token)

            # Check if the refresh token exists in the database and is valid
            stored_token = self.user_repo.get_refresh_token_by_hash(token_hash)
            if not stored_token:
                logger.warning(
                    f"Invalid or expired refresh token used for user {user_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired refresh token",
                )

            # Get the user
            user = self.user_repo.get_user_by_id(user_id)
            if not user:
                logger.warning(f"Refresh token used for non-existent user {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                )

            # Verify user is still admin
            if not self.user_repo.is_admin_user(user):
                logger.warning(
                    f"Non-admin user {user_id} ({user.email}) attempted to refresh token"
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Admin privileges required",
                )

            logger.info(f"Access token refreshed for user {user_id} ({user.email})")

            # SECURITY: Implement token rotation for enhanced security
            # Revoke the used refresh token immediately to prevent replay attacks
            self.user_repo.revoke_refresh_token(stored_token)

            # Create new access token
            access_token = create_access_token(
                data={"sub": str(user.id), "username": user.username, "role": user.role}
            )

            # Create new refresh token for rotation
            new_refresh_token = create_refresh_token(
                data={"sub": str(user.id), "username": user.username}
            )

            # Store new refresh token hash in database
            new_refresh_token_hash = hash_refresh_token(new_refresh_token)
            self.user_repo.store_refresh_token(user, new_refresh_token_hash)

            return TokenResponse(
                access_token=access_token,
                refresh_token=new_refresh_token,
                token_type="bearer",
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
            )

        except HTTPException:
            # Re-raise HTTP exceptions, but ensure token is revoked if we found it
            self._safely_revoke_refresh_token(stored_token, "failed refresh attempt")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {str(e)}")

            # Revoke the token if we found it to prevent replay attacks
            self._safely_revoke_refresh_token(stored_token, "unexpected error")

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )
