import io
import tempfile
from pathlib import Path
from typing import Any

import requests
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

from src.senda.api.models.lesson import Lesson
from src.senda.api.models.audio import AudioQualityThresholds
from src.senda.api.services.s3_service import S3Service

KOKORO_API_URL = "http://localhost:8880/v1/audio/speech"
MODEL_VOICE = "af_nicole"
MODEL_NAME = "kokoro"
RATE = 24000
CHANNELS = 1
SAMPLE_WIDTH = 2


class AudioService:
    def __init__(self, s3_service: S3Service):
        self.s3_service = s3_service

    def _get_speech_audio(self, text_to_speak: str):
        payload = {
            "model": MODEL_NAME,
            "input": text_to_speak,
            "voice": MODEL_VOICE,
            "response_format": "pcm",
            "stream": True,
        }
        headers = {"Content-Type": "application/json"}
        audio_chunks = []

        try:
            with requests.post(
                KOKORO_API_URL, headers=headers, json=payload, stream=True
            ) as response:
                response.raise_for_status()
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        audio_chunks.append(chunk)
        except requests.exceptions.RequestException as e:
            print(f"    API Error: {e}")
            return None

        return b"".join(audio_chunks)

    def _calculate_audio_metrics(
        self, audio: AudioSegment, lesson: Lesson, file_path: str
    ) -> dict[str, Any]:
        """Calculate comprehensive audio quality metrics"""
        # Basic metrics
        total_duration_seconds = len(audio) / 1000.0
        expected_duration_seconds = lesson.duration_minutes * 60.0
        file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)

        # Duration match
        duration_match_percentage = (
            total_duration_seconds / expected_duration_seconds * 100
        )

        # Calculate speech and silence durations from script
        silence_duration_ms = 0
        speech_segment_count = 0
        silence_segments = []

        for action in lesson.script:
            if action.get("type") == "speak":
                # Estimate speech duration (we'll calculate actual from audio)
                speech_segment_count += 1
            elif action.get("type") == "pause":
                duration_ms = int(action.get("duration", 0) * 1000)
                silence_duration_ms += duration_ms
                silence_segments.append(duration_ms / 1000.0)

        # Detect actual speech/silence using pydub
        # Consider anything below -40 dBFS as silence
        nonsilent_ranges = detect_nonsilent(
            audio, min_silence_len=100, silence_thresh=-40, seek_step=10
        )

        actual_speech_duration_ms = sum(end - start for start, end in nonsilent_ranges)
        actual_silence_duration_ms = len(audio) - actual_speech_duration_ms

        speech_duration_seconds = actual_speech_duration_ms / 1000.0
        silence_duration_seconds = actual_silence_duration_ms / 1000.0

        # Speech to silence ratio
        speech_to_silence_ratio = (
            speech_duration_seconds / silence_duration_seconds
            if silence_duration_seconds > 0
            else float("inf")
        )
        speech_percentage = (speech_duration_seconds / total_duration_seconds) * 100

        # Silence analysis
        silence_segment_count = len(silence_segments)
        longest_silence_seconds = max(silence_segments) if silence_segments else 0.0
        average_silence_seconds = (
            sum(silence_segments) / len(silence_segments) if silence_segments else 0.0
        )

        # Expected speech segment count from script
        expected_speech_segment_count = len(
            [part for part in lesson.script if part.get("type") == "speak"]
        )

        # Audio quality metrics
        average_loudness_dbfs = audio.dBFS
        peak_loudness_dbfs = audio.max_dBFS
        dynamic_range_db = peak_loudness_dbfs - average_loudness_dbfs

        # Validation based on thresholds
        is_duration_valid = (
            abs(100 - duration_match_percentage)
            <= AudioQualityThresholds.DURATION_TOLERANCE_PERCENTAGE
        )

        is_speech_ratio_valid = (
            AudioQualityThresholds.SPEECH_PERCENTAGE_MIN
            <= speech_percentage
            <= AudioQualityThresholds.SPEECH_PERCENTAGE_MAX
        )

        is_silence_gaps_valid = (
            longest_silence_seconds <= AudioQualityThresholds.MAX_SINGLE_SILENCE_SECONDS
        )

        is_segment_count_valid = (
            abs(speech_segment_count - expected_speech_segment_count)
            <= AudioQualityThresholds.SEGMENT_COUNT_TOLERANCE
        )

        is_loudness_valid = (
            AudioQualityThresholds.MIN_AVERAGE_LOUDNESS_DBFS
            <= average_loudness_dbfs
            <= AudioQualityThresholds.MAX_AVERAGE_LOUDNESS_DBFS
            and peak_loudness_dbfs >= AudioQualityThresholds.MIN_PEAK_LOUDNESS_DBFS
        )

        expected_mb = expected_duration_seconds / 60.0
        is_file_size_valid = (
            expected_mb * AudioQualityThresholds.MIN_MB_PER_MINUTE
            <= file_size_mb
            <= expected_mb * AudioQualityThresholds.MAX_MB_PER_MINUTE
        )

        # Overall quality check
        is_quality_valid = all(
            [
                is_duration_valid,
                is_speech_ratio_valid,
                is_silence_gaps_valid,
                is_segment_count_valid,
                is_loudness_valid,
                is_file_size_valid,
            ]
        )

        return {
            "file_size_mb": round(file_size_mb, 2),
            "total_duration_seconds": round(total_duration_seconds, 2),
            "expected_duration_seconds": round(expected_duration_seconds, 2),
            "duration_match_percentage": round(duration_match_percentage, 2),
            "speech_duration_seconds": round(speech_duration_seconds, 2),
            "silence_duration_seconds": round(silence_duration_seconds, 2),
            "speech_to_silence_ratio": round(speech_to_silence_ratio, 2),
            "speech_percentage": round(speech_percentage, 2),
            "silence_segment_count": silence_segment_count,
            "longest_silence_seconds": round(longest_silence_seconds, 2),
            "average_silence_seconds": round(average_silence_seconds, 2),
            "speech_segment_count": speech_segment_count,
            "expected_speech_segment_count": expected_speech_segment_count,
            "average_loudness_dbfs": round(average_loudness_dbfs, 2),
            "peak_loudness_dbfs": round(peak_loudness_dbfs, 2),
            "dynamic_range_db": round(dynamic_range_db, 2),
            "is_duration_valid": is_duration_valid,
            "is_speech_ratio_valid": is_speech_ratio_valid,
            "is_silence_gaps_valid": is_silence_gaps_valid,
            "is_segment_count_valid": is_segment_count_valid,
            "is_loudness_valid": is_loudness_valid,
            "is_file_size_valid": is_file_size_valid,
            "is_quality_valid": is_quality_valid,
        }

    def generate_and_upload_lesson_audio(
        self, lesson: Lesson
    ) -> tuple[str, dict[str, Any]] | tuple[None, None]:
        if not lesson.script or not isinstance(lesson.script, list):
            return None, None

        final_audio = AudioSegment.empty()

        for action in lesson.script:
            if action.get("type") == "speak":
                speech_data = self._get_speech_audio(action.get("content", ""))
                if speech_data:
                    speech_segment = AudioSegment.from_raw(
                        io.BytesIO(speech_data),
                        sample_width=SAMPLE_WIDTH,
                        frame_rate=RATE,
                        channels=CHANNELS,
                    )
                    final_audio += speech_segment

            elif action.get("type") == "pause":
                duration_ms = int(action.get("duration", 0) * 1000)
                silence_segment = AudioSegment.silent(
                    duration=duration_ms, frame_rate=RATE
                )
                final_audio += silence_segment

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            final_audio.export(tmp_file.name, format="mp3")

            # Calculate metrics before upload
            metrics = self._calculate_audio_metrics(final_audio, lesson, tmp_file.name)

            random_string = self.s3_service.generate_s3_safe_random_string_random()
            object_name = f"audio/{lesson.id}_{lesson.title.replace(' ', '_')}_{random_string}.mp3"
            s3_url = self.s3_service.upload_file(
                file_path=tmp_file.name,
                object_name=object_name,
            )

        Path(tmp_file.name).unlink()

        return s3_url, metrics
