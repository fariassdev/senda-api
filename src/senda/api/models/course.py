from sqlalchemy import Column, Integer, String, Boolean, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, column_property
from src.senda.api.models.lesson import Lesson
from src.senda.api.core.database import Base


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


Course.total_lessons = column_property(
    select(func.count(Lesson.id))
    .where(Lesson.course_id == Course.id)
    .correlate_except(Lesson)
    .scalar_subquery()
)
