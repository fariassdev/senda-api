from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from src.senda.api.core.database import Base
import enum


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

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    lesson_number = Column(Integer, index=True)
    title = Column(String)
    core_practice = Column(String)
    key_point = Column(String)
    tone = Column(String)
    duration_minutes = Column(Integer)
    status = Column(String, default=LessonStatus.PENDING)
    script = Column(JSONB, nullable=True)
    audio_url = Column(String, nullable=True)

    course = relationship("Course", back_populates="lessons")
