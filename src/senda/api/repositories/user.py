"""
User repository for database operations.

This module provides the database layer for user-related operations
including authentication, user management, and security features.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from src.senda.api.models.user import User, UserRole
from src.senda.api.models.refresh_token import RefreshToken
from src.senda.api.core.auth import (
    MAX_LOGIN_ATTEMPTS,
    ACCOUNT_LOCKOUT_DURATION_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)


class UserRepository:
    """Repository for user database operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_user_by_email_or_username(self, email_or_username: str) -> Optional[User]:
        """
        Get user by email or username.

        Args:
            email_or_username: Email address or username to search for

        Returns:
            User instance if found, None otherwise
        """
        return (
            self.db.query(User)
            .filter(
                or_(User.email == email_or_username, User.username == email_or_username)
            )
            .first()
        )

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User ID to search for

        Returns:
            User instance if found, None otherwise
        """
        return self.db.query(User).filter(User.id == user_id).first()

    def is_account_locked(self, user: User) -> bool:
        """
        Check if user account is locked due to failed login attempts.

        Args:
            user: User instance to check

        Returns:
            True if account is locked, False otherwise
        """
        if user.account_locked_until is None:
            return False

        return user.account_locked_until > datetime.now(timezone.utc)

    def increment_failed_login_attempts(self, user: User) -> None:
        """
        Increment failed login attempts and lock account if necessary.

        Args:
            user: User instance to update
        """
        user.failed_login_attempts += 1

        # Lock account if max attempts reached
        if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
            user.account_locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=ACCOUNT_LOCKOUT_DURATION_MINUTES
            )

        self.db.commit()

    def reset_failed_login_attempts(self, user: User) -> None:
        """
        Reset failed login attempts and unlock account.

        Args:
            user: User instance to update
        """
        user.failed_login_attempts = 0
        user.account_locked_until = None
        user.last_login = datetime.now(timezone.utc)
        self.db.commit()

    def is_admin_user(self, user: User) -> bool:
        """
        Check if user has admin role.

        Args:
            user: User instance to check

        Returns:
            True if user is admin, False otherwise
        """
        return user.role == UserRole.ADMIN

    def store_refresh_token(self, user: User, token_hash: str) -> RefreshToken:
        """
        Store a refresh token for a user.

        Args:
            user: User instance
            token_hash: Hashed refresh token

        Returns:
            Created RefreshToken instance
        """
        # Clean up any expired tokens for this user
        self.cleanup_expired_refresh_tokens(user)

        # Create new refresh token
        refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )

        self.db.add(refresh_token)
        self.db.commit()
        self.db.refresh(refresh_token)

        return refresh_token

    def get_refresh_token_by_hash(self, token_hash: str) -> Optional[RefreshToken]:
        """
        Get refresh token by its hash.

        Args:
            token_hash: Hashed refresh token

        Returns:
            RefreshToken instance if found and valid, None otherwise
        """
        return (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.token_hash == token_hash,
                RefreshToken.is_revoked.is_(False),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
            .first()
        )

    def revoke_refresh_token(self, refresh_token: RefreshToken) -> None:
        """
        Revoke a refresh token.

        Args:
            refresh_token: RefreshToken instance to revoke
        """
        refresh_token.revoke()
        self.db.commit()

    def cleanup_expired_refresh_tokens(self, user: User) -> None:
        """
        Clean up expired refresh tokens for a user.

        Args:
            user: User instance
        """
        expired_tokens = (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.user_id == user.id,
                RefreshToken.expires_at <= datetime.now(timezone.utc),
            )
            .all()
        )

        for token in expired_tokens:
            self.db.delete(token)

        self.db.commit()
