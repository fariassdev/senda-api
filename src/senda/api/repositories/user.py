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
from src.senda.api.core.auth import MAX_LOGIN_ATTEMPTS, ACCOUNT_LOCKOUT_DURATION_MINUTES


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
