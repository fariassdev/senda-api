from sqlalchemy import Column, String, ForeignKey, Integer, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from src.senda.api.core.database import Base
from src.senda.api.utils.uuid_utils import generate_uuidv7
import enum
from sqlalchemy.sql import func


class LessonStatus(str, enum.Enum):
    PENDING = "PENDING"
    SCRIPT_GENERATING = "SCRIPT_GENERATING"
    SCRIPT_COMPLETED = "SCRIPT_COMPLETED"
    SCRIPT_FAILED = "SCRIPT_FAILED"
    AUDIO_GENERATING = "AUDIO_GENERATING"
    AUDIO_COMPLETED = "AUDIO_COMPLETED"
    AUDIO_FAILED = "AUDIO_FAILED"


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(
        UUID(as_uuid=True), primary_key=True, index=True, default=generate_uuidv7
    )
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"))
    lesson_number = Column(Integer, index=True)
    title = Column(String)
    core_practice = Column(String)
    key_point = Column(String)
    tone = Column(String)
    duration_minutes = Column(Integer)
    status = Column(String, default=LessonStatus.PENDING)
    script = Column(JSONB, nullable=True)
    script_generated_at = Column(DateTime(timezone=True), nullable=True)

    course = relationship("Course", back_populates="lessons")
    audio = relationship("Audio", back_populates="lesson", uselist=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
