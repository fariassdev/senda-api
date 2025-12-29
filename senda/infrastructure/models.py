import enum
from datetime import datetime
from functools import partial

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
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

    # Relationships
    created_jobs: Mapped[list["GenerationJob"]] = relationship(back_populates="creator")


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

    # Relationships
    generation_jobs: Mapped[list["GenerationJob"]] = relationship(
        back_populates="course"
    )


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

    # Relationships
    generation_jobs: Mapped[list["GenerationJob"]] = relationship(
        back_populates="lesson"
    )


class GenerationJob(Base):
    """
    Async generation job for course structure, script, and audio generation.

    This model tracks the lifecycle of AI-powered generation tasks, supporting:
    - Course structure generation (creates lessons from course description)
    - Script generation (creates lesson scripts using Gemini)
    - Audio generation (creates audio files using Kokoro TTS)

    Relationships:
    - course: The course this job belongs to (CASCADE delete)
    - lesson: The specific lesson being generated, if applicable (SET NULL on delete)
    - creator: The user who initiated the job (CASCADE delete)

    Indexes:
    - idx_generation_job_status: For filtering jobs by status
    - idx_generation_job_course_id: For listing jobs by course
    - idx_generation_job_created_at: For sorting by creation date (DESC)
    """

    __tablename__ = "generation_job"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Job type with enum validation and VARCHAR(50) constraint
    job_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Job type: course_structure, script, or audio",
    )

    # Foreign keys with documented cascade behavior
    course_id: Mapped[int] = mapped_column(
        ForeignKey("course.id", ondelete="CASCADE"),
        nullable=False,
        comment="FK to course - CASCADE: job deleted when course deleted",
    )
    lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("lesson.id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to lesson - SET NULL: job remains if lesson deleted",
    )

    # Status with enum validation and VARCHAR(20) constraint
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=JobStatus.PENDING.value,
        server_default=text("'pending'"),
        comment="Job status: pending, processing, completed, or failed",
    )

    # Job data stored as JSONB for efficient PostgreSQL querying
    payload: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Input parameters for the generation task"
    )
    result: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Output data or error details from the generation task",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Human-readable error message if job failed"
    )

    # Timestamps with server defaults
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="When the job was created",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the job started processing",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the job completed (success or failure)",
    )

    # User who created the job
    created_by: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        comment="FK to user - CASCADE: job deleted when user deleted",
    )

    # Relationships (using lazy="raise" via partial at module level)
    course: Mapped["Course"] = relationship(back_populates="generation_jobs")
    lesson: Mapped["Lesson | None"] = relationship(back_populates="generation_jobs")
    creator: Mapped["User"] = relationship(back_populates="created_jobs")

    # Indexes for query performance
    __table_args__ = (
        Index("idx_generation_job_status", "status"),
        Index("idx_generation_job_course_id", "course_id"),
        Index("idx_generation_job_created_at", created_at.desc()),
    )

    def validate_job_type(self) -> bool:
        """Validate that job_type is a valid JobType enum value."""
        try:
            JobType(self.job_type)
            return True
        except ValueError:
            return False

    def validate_status(self) -> bool:
        """Validate that status is a valid JobStatus enum value."""
        try:
            JobStatus(self.status)
            return True
        except ValueError:
            return False
