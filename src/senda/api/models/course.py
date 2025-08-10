from sqlalchemy import Column, Integer, String, Enum, ForeignKey
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

    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    author = Column(String)
    image_placeholder_url = Column(String)

    lessons = relationship(
        "Lesson", back_populates="course", cascade="all, delete-orphan"
    )


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(String, ForeignKey("courses.id"))
    lesson_number = Column(Integer, index=True)
    title = Column(String)
    core_practice = Column(String)
    key_point = Column(String)
    tone = Column(String)
    duration_minutes = Column(Integer)
    status = Column(Enum(LessonStatus), default=LessonStatus.NOT_GENERATED)
    script_url = Column(String, nullable=True)
    audio_url = Column(String, nullable=True)

    course = relationship("Course", back_populates="lessons")
