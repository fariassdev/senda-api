from sqlalchemy import Column, String, ForeignKey, Float, Integer, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.senda.api.core.database import Base
from src.senda.api.utils.uuid_utils import generate_uuidv7
from sqlalchemy.sql import func


class Audio(Base):
    __tablename__ = "audios"

    id = Column(
        UUID(as_uuid=True), primary_key=True, index=True, default=generate_uuidv7
    )
    lesson_id = Column(
        UUID(as_uuid=True), ForeignKey("lessons.id"), unique=True, nullable=False
    )
    url = Column(String, nullable=False)
    file_size_mb = Column(Float, nullable=False)

    # Duration metrics
    total_duration_seconds = Column(Float, nullable=False)
    expected_duration_seconds = Column(Float, nullable=False)
    duration_match_percentage = Column(Float, nullable=False)

    # Speech/Silence metrics
    speech_duration_seconds = Column(Float, nullable=False)
    silence_duration_seconds = Column(Float, nullable=False)
    speech_to_silence_ratio = Column(Float, nullable=False)
    speech_percentage = Column(Float, nullable=False)

    # Silence analysis
    silence_segment_count = Column(Integer, nullable=False)
    longest_silence_seconds = Column(Float, nullable=False)
    average_silence_seconds = Column(Float, nullable=False)

    # Speech analysis
    speech_segment_count = Column(Integer, nullable=False)
    expected_speech_segment_count = Column(Integer, nullable=False)

    # Audio quality
    average_loudness_dbfs = Column(Float, nullable=False)
    peak_loudness_dbfs = Column(Float, nullable=False)
    dynamic_range_db = Column(Float, nullable=False)

    # Validation flags (calculated based on thresholds)
    is_duration_valid = Column(Boolean, nullable=False)
    is_speech_ratio_valid = Column(Boolean, nullable=False)
    is_silence_gaps_valid = Column(Boolean, nullable=False)
    is_segment_count_valid = Column(Boolean, nullable=False)
    is_loudness_valid = Column(Boolean, nullable=False)
    is_file_size_valid = Column(Boolean, nullable=False)

    # Overall validation
    is_quality_valid = Column(Boolean, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    lesson = relationship("Lesson", back_populates="audio", uselist=False)


# Quality thresholds for validation
class AudioQualityThresholds:
    """Thresholds for detecting audio quality issues"""

    # Duration validation: within ±15% of expected
    DURATION_TOLERANCE_PERCENTAGE = 15.0

    # Speech ratio: 40-70% speech is typical for meditation
    SPEECH_PERCENTAGE_MIN = 35.0
    SPEECH_PERCENTAGE_MAX = 75.0

    # Silence gaps: no single silence should exceed this (except for very long meditations)
    MAX_SINGLE_SILENCE_SECONDS = 45.0

    # Segment count: should match script within tolerance
    SEGMENT_COUNT_TOLERANCE = 2  # Allow ±2 segments difference

    # Loudness: avoid too quiet or clipping
    MIN_AVERAGE_LOUDNESS_DBFS = -40.0
    MAX_AVERAGE_LOUDNESS_DBFS = -10.0
    MIN_PEAK_LOUDNESS_DBFS = -6.0  # Should not clip (0 dBFS)

    # Dynamic range: ensure audio has proper dynamics
    MIN_DYNAMIC_RANGE_DB = 4.0
    MAX_DYNAMIC_RANGE_DB = 20.0

    # File size: rough estimate of ~0.8-1.2 MB per minute for MP3
    MIN_MB_PER_MINUTE = 0.5
    MAX_MB_PER_MINUTE = 2.0
