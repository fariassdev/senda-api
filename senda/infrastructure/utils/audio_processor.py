"""Audio processing utilities for combining and exporting audio segments."""

import io
import logging
import tempfile
from pathlib import Path

from pydub import AudioSegment

from senda.core.enums import ScriptPartType
from senda.domain.dtos.script_generation import ScriptPartDTO

logger = logging.getLogger(__name__)

SAMPLE_RATE = 24000
CHANNELS = 1
SAMPLE_WIDTH = 2


class AudioProcessor:
    """Utility class for processing and combining audio segments.

    This class handles converting raw PCM audio data from TTS into
    AudioSegment objects, adding silence/pause segments, and exporting
    the final combined audio as MP3.
    """

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        channels: int = CHANNELS,
        sample_width: int = SAMPLE_WIDTH,
    ) -> None:
        """Initialize the audio processor.

        Args:
            sample_rate: Sample rate in Hz (default: 24000)
            channels: Number of audio channels (default: 1 for mono)
            sample_width: Sample width in bytes (default: 2 for 16-bit)
        """
        self._sample_rate = sample_rate
        self._channels = channels
        self._sample_width = sample_width

        logger.info(
            f"Initialized AudioProcessor (rate={sample_rate}Hz, "
            f"channels={channels}, width={sample_width} bytes)"
        )

    def pcm_to_audio_segment(self, pcm_data: bytes) -> AudioSegment:
        """Convert raw PCM audio data to AudioSegment.

        Args:
            pcm_data: Raw PCM audio bytes

        Returns:
            AudioSegment object

        Raises:
            ValueError: If PCM data is invalid
        """
        if not pcm_data:
            raise ValueError("PCM data is empty")

        try:
            audio_segment = AudioSegment.from_raw(
                io.BytesIO(pcm_data),
                sample_width=self._sample_width,
                frame_rate=self._sample_rate,
                channels=self._channels,
            )
            logger.debug(
                f"Converted PCM to AudioSegment: {len(audio_segment)}ms duration"
            )
            return audio_segment
        except Exception as e:
            logger.error(f"Failed to convert PCM to AudioSegment: {e}")
            raise ValueError(f"Invalid PCM data: {e}") from e

    def create_silence(self, duration_seconds: float) -> AudioSegment:
        """Create a silent audio segment of specified duration.

        Args:
            duration_seconds: Duration of silence in seconds

        Returns:
            Silent AudioSegment

        Raises:
            ValueError: If duration is negative
        """
        if duration_seconds < 0:
            raise ValueError("Duration cannot be negative")

        duration_ms = int(duration_seconds * 1000)
        silence = AudioSegment.silent(
            duration=duration_ms, frame_rate=self._sample_rate
        )
        logger.debug(f"Created silence segment: {duration_ms}ms")
        return silence

    def combine_script_parts(
        self, script_parts: list[ScriptPartDTO], speech_data: dict[int, bytes]
    ) -> AudioSegment:
        """Combine script parts into a single audio segment using pre-generated speech data.

        This method processes each script part, converting raw PCM audio data from the
        provided speech_data map for "speak" parts and adding silence for "pause" parts.

        Args:
            script_parts: List of script parts to process
            speech_data: Dictionary mapping script part index to raw PCM audio bytes

        Returns:
            Combined AudioSegment

        Raises:
            ValueError: If script parts are invalid
        """
        if not script_parts:
            raise ValueError("No script parts provided")

        logger.info(f"Combining {len(script_parts)} script parts into audio")

        final_audio = AudioSegment.empty()

        for idx, part in enumerate(script_parts):
            logger.debug(f"Combining part {idx + 1}/{len(script_parts)}: {part.type}")

            if part.type == ScriptPartType.SPEAK:
                if idx not in speech_data or not speech_data[idx]:
                    logger.warning(f"Part {idx + 1} has no generated speech, skipping")
                    continue

                speech_segment = self.pcm_to_audio_segment(speech_data[idx])
                final_audio += speech_segment

            elif part.type == ScriptPartType.PAUSE:
                if part.duration is None or part.duration <= 0:
                    logger.warning(f"Part {idx + 1} has invalid duration, skipping")
                    continue

                silence_segment = self.create_silence(part.duration)
                final_audio += silence_segment

            else:
                logger.warning(f"Unknown script part type: {part.type}, skipping")
                continue

        logger.info(
            f"Combined audio complete: {len(final_audio)}ms total duration, "
            f"{len(final_audio.raw_data)} bytes"
        )
        return final_audio

    def export_to_mp3(self, audio: AudioSegment) -> bytes:
        """Export AudioSegment to MP3 format.

        Args:
            audio: AudioSegment to export

        Returns:
            MP3 audio data as bytes

        Raises:
            RuntimeError: If export fails (e.g., ffmpeg not installed)
        """
        if not audio:
            raise ValueError("Audio segment is empty")

        logger.info("Exporting audio to MP3 format")

        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_path = Path(tmp_file.name)

            audio.export(str(tmp_path), format="mp3")
            mp3_data = tmp_path.read_bytes()
            tmp_path.unlink()

            logger.info(f"Successfully exported MP3: {len(mp3_data)} bytes")
            return mp3_data

        except FileNotFoundError as e:
            logger.error("ffmpeg not found - required for MP3 export")
            raise RuntimeError(
                "ffmpeg is not installed or not in PATH. "
                "Please install ffmpeg to export audio."
            ) from e

        except Exception as e:
            logger.exception(f"Failed to export audio to MP3: {e}")
            raise RuntimeError(f"Audio export failed: {e}") from e
