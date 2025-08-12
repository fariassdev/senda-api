from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, column_property
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


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    tags = Column(JSONB)
    active = Column(Boolean, default=False, nullable=False)

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
    status = Column(String, default=LessonStatus.PENDING)
    script = Column(JSONB, nullable=True)
    audio_url = Column(String, nullable=True)

    course = relationship("Course", back_populates="lessons")


Course.total_lessons = column_property(
    select(func.count(Lesson.id))
    .where(Lesson.course_id == Course.id)
    .correlate_except(Lesson)
    .scalar_subquery()
)
