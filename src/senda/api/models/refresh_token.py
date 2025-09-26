from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.senda.api.core.database import Base
from src.senda.api.utils.uuid_utils import generate_uuidv7


class RefreshToken(Base):
    """
    Refresh token model for JWT token management.

    Stores refresh tokens with expiration and revocation capabilities
    for secure token rotation.
    """

    __tablename__ = "refresh_tokens"

    id = Column(
        UUID(as_uuid=True), primary_key=True, index=True, default=generate_uuidv7
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = Column(String(255), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    is_revoked = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

    def revoke(self):
        """Mark the token as revoked."""
        self.is_revoked = True
        self.revoked_at = func.now()

    def is_valid(self) -> bool:
        """Check if the token is still valid."""
        if self.is_revoked:
            return False
        return self.expires_at > func.now()
