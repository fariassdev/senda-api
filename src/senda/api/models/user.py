from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.senda.api.core.database import Base
from src.senda.api.utils.uuid_utils import generate_uuidv7
import enum


class UserRole(str, enum.Enum):
    """Available user roles."""

    ADMIN = "admin"
    # Future roles can be added here


class User(Base):
    """
    User model for admin authentication.

    This model stores admin user accounts with security features
    including account locking, password policies, and audit trails.
    """

    __tablename__ = "users"

    # Primary identifiers
    id = Column(
        UUID(as_uuid=True), primary_key=True, index=True, default=generate_uuidv7
    )
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)

    # Authentication
    password_hash = Column(String(255), nullable=False)

    # Profile information
    name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default=UserRole.ADMIN, index=True)

    # Security & Account Protection
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    account_locked_until = Column(DateTime(timezone=True), nullable=True, index=True)
    last_login = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )

    def is_account_locked(self) -> bool:
        """Check if the account is currently locked."""
        if self.account_locked_until is None:
            return False
        return self.account_locked_until > func.now()

    def increment_failed_login(
        self, max_attempts: int = 5, lockout_duration_minutes: int = 30
    ):
        """Increment failed login attempts and lock account if needed."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            from datetime import datetime, timedelta, timezone

            self.account_locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=lockout_duration_minutes
            )

    def reset_failed_login_attempts(self):
        """Reset failed login attempts after successful login."""
        self.failed_login_attempts = 0
        self.account_locked_until = None
