from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from src.senda.api.core.database import Base
from src.senda.api.utils.uuid_utils import generate_uuidv7
from sqlalchemy.sql import func


class Course(Base):
    __tablename__ = "courses"

    id = Column(
        UUID(as_uuid=True), primary_key=True, index=True, default=generate_uuidv7
    )
    title = Column(String, index=True)
    description = Column(String)
    tags = Column(JSONB)
    active = Column(Boolean, default=False, nullable=False)

    author = Column(String, default="Senda AI")
    image_placeholder_url = Column(String, nullable=True)

    lessons = relationship(
        "Lesson", back_populates="course", cascade="all, delete-orphan"
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
