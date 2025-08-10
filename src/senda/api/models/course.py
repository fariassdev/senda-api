from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from src.senda.api.core.database import Base
import enum


class LessonStatus(str, enum.Enum):
    NOT_GENERATED = "NOT_GENERATED"
    GENERATING = "GENERATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    total_lessons = Column(Integer)
    tags = Column(JSONB)  # Using JSONB for storing tags as a list of strings
    active = Column(Boolean, default=False, nullable=False)

    # Fields to be managed outside the LLM generation
    author = Column(String, default="Senda AI")
    image_placeholder_url = Column(String, nullable=True)

    lessons = relationship(
        "Lesson", back_populates="course", cascade="all, delete-orphan"
    )


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
    status = Column(String, default=LessonStatus.NOT_GENERATED)
    script_url = Column(String, nullable=True)
    audio_url = Column(String, nullable=True)

    course = relationship("Course", back_populates="lessons")
