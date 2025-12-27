import enum
from datetime import datetime
from functools import partial

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from senda.core.enums import JobStatus, JobType, LessonStatus, UserRole


class Base(DeclarativeBase):
    pass


relationship = partial(relationship, lazy="raise")


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    bio: Mapped[str] = mapped_column(nullable=True)
    image_url: Mapped[str] = mapped_column(nullable=True)
    name: Mapped[str] = mapped_column(nullable=True)
    role: Mapped[str] = mapped_column(default=UserRole.USER)

    # Security fields
    failed_login_attempts: Mapped[int] = mapped_column(default=0)
    account_locked_until: Mapped[datetime] = mapped_column(nullable=True)
    last_login: Mapped[datetime] = mapped_column(nullable=True)

    created_at: Mapped[datetime]
    updated_at: Mapped[datetime] = mapped_column(nullable=True)


class Follower(Base):
    __tablename__ = "follower"

    # "follower" is a user who follows a user.
    follower_id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)
    # "following" is a user who you follow.
    following_id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)
    created_at: Mapped[datetime]


class Course(Base):
    __tablename__ = "course"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    slug: Mapped[str] = mapped_column(nullable=False, unique=True)
    title: Mapped[str]
    description: Mapped[str]
    difficulty_level: Mapped[str] = mapped_column(default="BEGINNER")
    active: Mapped[bool] = mapped_column(default=False)
    image_placeholder_url: Mapped[str] = mapped_column(nullable=True)

    created_at: Mapped[datetime]
    updated_at: Mapped[datetime] = mapped_column(nullable=True)


class Tag(Base):
    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tag: Mapped[str] = mapped_column(nullable=False, unique=True)
    created_at: Mapped[datetime]


class CourseTag(Base):
    __tablename__ = "course_tag"

    course_id: Mapped[int] = mapped_column(
        ForeignKey("course.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), primary_key=True)
    created_at: Mapped[datetime]


class Favorite(Base):
    __tablename__ = "favorite"

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("course.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime]


class Lesson(Base):
    __tablename__ = "lesson"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("course.id", ondelete="CASCADE"), nullable=False
    )

    # Ordering
    lesson_number: Mapped[int]

    # Content
    title: Mapped[str]
    core_practice: Mapped[str]
    key_point: Mapped[str]
    tone: Mapped[str]
    duration_minutes: Mapped[int]

    # Generation workflow
    status: Mapped[str] = mapped_column(default=LessonStatus.PENDING.value)

    # Generated content (nullable until generated)
    script: Mapped[str] = mapped_column(nullable=True)  # JSON stored as text
    audio_url: Mapped[str] = mapped_column(nullable=True)
    script_generated_at: Mapped[datetime] = mapped_column(nullable=True)
    audio_generated_at: Mapped[datetime] = mapped_column(nullable=True)

    created_at: Mapped[datetime]
    updated_at: Mapped[datetime] = mapped_column(nullable=True)


class GenerationJob(Base):
    """Async generation job for course structure, script, and audio generation."""

    __tablename__ = "generation_job"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(nullable=False)  # JobType enum value
    course_id: Mapped[int] = mapped_column(
        ForeignKey("course.id", ondelete="CASCADE"), nullable=False
    )
    lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("lesson.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(nullable=False, default=JobStatus.PENDING.value)

    # Job data
    payload: Mapped[str | None] = mapped_column(nullable=True)  # JSON stored as text
    result: Mapped[str | None] = mapped_column(nullable=True)  # JSON stored as text
    error_message: Mapped[str | None] = mapped_column(nullable=True)

    # Timestamps
    created_at: Mapped[datetime]
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # User who created the job
    created_by: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
