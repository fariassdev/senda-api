import enum
from datetime import datetime
from functools import partial
from uuid import UUID, uuid4

from sqlalchemy import Float, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from senda.core.enums import AudioGenerationJobStatus, LessonStatus, UserRole


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
    script_generated_at: Mapped[datetime] = mapped_column(nullable=True)

    created_at: Mapped[datetime]
    updated_at: Mapped[datetime] = mapped_column(nullable=True)


class LessonAudio(Base):
    __tablename__ = "lesson_audio"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("lesson.id", ondelete="CASCADE"), nullable=False
    )
    voice_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("voices.id"), nullable=True
    )
    voice_slug: Mapped[str | None] = mapped_column(nullable=True)
    audio_provider: Mapped[str | None] = mapped_column(nullable=True)
    playlist_url: Mapped[str] = mapped_column(nullable=False)
    hls_base_path: Mapped[str] = mapped_column(nullable=False)
    segment_count: Mapped[int] = mapped_column(nullable=False)
    duration_ms: Mapped[int] = mapped_column(nullable=False)
    generated_at: Mapped[datetime] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.now, onupdate=datetime.now
    )


class AudioGenerationJob(Base):
    __tablename__ = "audio_generation_jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lesson.id"), nullable=False)
    voice_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("voices.id"), nullable=True
    )
    voice_slug: Mapped[str | None] = mapped_column(nullable=True)
    audio_provider: Mapped[str | None] = mapped_column(nullable=True)
    s3_base_path: Mapped[str] = mapped_column(nullable=False)
    speed: Mapped[float] = mapped_column(default=1.0)
    status: Mapped[str] = mapped_column(default=AudioGenerationJobStatus.PENDING.value)
    segments_available: Mapped[int] = mapped_column(default=0)
    segment_count: Mapped[int | None] = mapped_column(nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    lesson_audio_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("lesson_audio.id"), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)


class Voice(Base):
    __tablename__ = "voices"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(nullable=False)
    slug: Mapped[str] = mapped_column(unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(nullable=False, default="es")
    gender: Mapped[str] = mapped_column(nullable=False)  # 'female' | 'male' | 'neutral'
    reference_s3_key: Mapped[str] = mapped_column(nullable=False)
    sample_s3_key: Mapped[str | None] = mapped_column(nullable=True)
    tts_provider: Mapped[str] = mapped_column(nullable=False, default="chatterbox")

    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.now, onupdate=datetime.now
    )
