from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class AudioMetrics(BaseModel):
    """Audio quality metrics"""

    # File info
    file_size_mb: float

    # Duration metrics
    total_duration_seconds: float
    expected_duration_seconds: float
    duration_match_percentage: float

    # Speech/Silence metrics
    speech_duration_seconds: float
    silence_duration_seconds: float
    speech_to_silence_ratio: float
    speech_percentage: float

    # Silence analysis
    silence_segment_count: int
    longest_silence_seconds: float
    average_silence_seconds: float

    # Speech analysis
    speech_segment_count: int
    expected_speech_segment_count: int

    # Audio quality
    average_loudness_dbfs: float
    peak_loudness_dbfs: float
    dynamic_range_db: float

    # Validation flags
    is_duration_valid: bool
    is_speech_ratio_valid: bool
    is_silence_gaps_valid: bool
    is_segment_count_valid: bool
    is_loudness_valid: bool
    is_file_size_valid: bool
    is_quality_valid: bool


class Audio(BaseModel):
    """Audio response model"""

    id: UUID
    lesson_id: UUID
    url: str
    file_size_mb: float

    # Duration metrics
    total_duration_seconds: float
    expected_duration_seconds: float
    duration_match_percentage: float

    # Speech/Silence metrics
    speech_duration_seconds: float
    silence_duration_seconds: float
    speech_to_silence_ratio: float
    speech_percentage: float

    # Silence analysis
    silence_segment_count: int
    longest_silence_seconds: float
    average_silence_seconds: float

    # Speech analysis
    speech_segment_count: int
    expected_speech_segment_count: int

    # Audio quality
    average_loudness_dbfs: float
    peak_loudness_dbfs: float
    dynamic_range_db: float

    # Validation flags
    is_duration_valid: bool
    is_speech_ratio_valid: bool
    is_silence_gaps_valid: bool
    is_segment_count_valid: bool
    is_loudness_valid: bool
    is_file_size_valid: bool
    is_quality_valid: bool

    # Timestamps
    created_at: datetime

    class Config:
        from_attributes = True
