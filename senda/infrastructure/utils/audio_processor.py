"""Audio processing utilities for combining and exporting audio segments."""

import asyncio
import io
import logging
import tempfile
from collections.abc import Awaitable, Callable
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
        max_concurrent_tts: int = 3,
    ) -> None:
        """Initialize the audio processor.

        Args:
            sample_rate: Sample rate in Hz (default: 24000)
            channels: Number of audio channels (default: 1 for mono)
            sample_width: Sample width in bytes (default: 2 for 16-bit)
            max_concurrent_tts: Max concurrent TTS requests (default: 3)
        """
        self._sample_rate = sample_rate
        self._channels = channels
        self._sample_width = sample_width
        self._max_concurrent_tts = max_concurrent_tts

        logger.info(
            f"Initialized AudioProcessor (rate={sample_rate}Hz, "
            f"channels={channels}, width={sample_width} bytes, "
            f"max_concurrent_tts={max_concurrent_tts})"
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

    async def combine_script_parts(
        self,
        script_parts: list[ScriptPartDTO],
        speech_generator: Callable[[str, str | None, float], Awaitable[bytes]],
        parallel: bool = True,
        voice: str | None = None,
        speed: float = 1.0,
    ) -> AudioSegment:
        """Combine script parts into a single audio segment.

        This method processes each script part, generating speech for "speak"
        parts and adding silence for "pause" parts.

        Args:
            script_parts: List of script parts to process
            speech_generator: Async callable that generates speech bytes from text
                             Should have signature: async def (text, voice, speed) -> bytes
            parallel: Whether to generate TTS for all parts in parallel (default: True)
                     If False, parts are processed sequentially
            voice: Optional voice override for TTS
            speed: Speech rate multiplier (0.5 to 2.0, default 1.0)

        Returns:
            Combined AudioSegment

        Raises:
            ValueError: If script parts are invalid
        """
        if not script_parts:
            raise ValueError("No script parts provided")

        logger.info(
            f"Combining {len(script_parts)} script parts into audio "
            f"(parallel={parallel}, max_concurrent={self._max_concurrent_tts})"
        )

        if parallel:
            return await self._combine_script_parts_parallel(
                script_parts, speech_generator, voice, speed
            )
        else:
            return await self._combine_script_parts_sequential(
                script_parts, speech_generator, voice, speed
            )

    async def _combine_script_parts_sequential(
        self,
        script_parts: list[ScriptPartDTO],
        speech_generator: Callable[[str, str | None, float], Awaitable[bytes]],
        voice: str | None = None,
        speed: float = 1.0,
    ) -> AudioSegment:
        """Combine script parts sequentially (original behavior)."""
        final_audio = AudioSegment.empty()

        for idx, part in enumerate(script_parts):
            logger.debug(f"Processing part {idx + 1}/{len(script_parts)}: {part.type}")

            if part.type == ScriptPartType.SPEAK:
                if not part.content:
                    logger.warning(f"Part {idx + 1} has no content, skipping")
                    continue

                speech_bytes = await speech_generator(part.content, voice, speed)
                speech_segment = self.pcm_to_audio_segment(speech_bytes)
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

    async def _combine_script_parts_parallel(
        self,
        script_parts: list[ScriptPartDTO],
        speech_generator: Callable[[str, str | None, float], Awaitable[bytes]],
        voice: str | None = None,
        speed: float = 1.0,
    ) -> AudioSegment:
        """Combine script parts with parallel TTS generation.

        This method generates TTS for all "speak" parts in parallel (with semaphore
        control), then combines them in order with pause segments.
        """
        # Create semaphore to limit concurrent TTS requests
        semaphore = asyncio.Semaphore(self._max_concurrent_tts)

        # Prepare tasks for all speak parts
        async def generate_speech_with_semaphore(
            idx: int, content: str
        ) -> tuple[int, bytes | None]:
            """Generate speech with semaphore control."""
            async with semaphore:
                try:
                    logger.debug(f"Generating TTS for part {idx + 1}")
                    speech_bytes = await speech_generator(content, voice, speed)
                    return (idx, speech_bytes)
                except Exception as e:
                    logger.error(f"Failed to generate TTS for part {idx + 1}: {e}")
                    return (idx, None)

        # Collect all speak tasks
        speak_tasks = []
        for idx, part in enumerate(script_parts):
            if part.type == ScriptPartType.SPEAK and part.content:
                speak_tasks.append(generate_speech_with_semaphore(idx, part.content))

        # Generate all TTS in parallel
        logger.info(f"Generating TTS for {len(speak_tasks)} speak parts in parallel")
        tts_results = await asyncio.gather(*speak_tasks)

        # Build a map of index -> speech_bytes
        speech_map: dict[int, bytes] = {
            idx: speech_bytes
            for idx, speech_bytes in tts_results
            if speech_bytes is not None
        }

        # Now combine parts in order
        final_audio = AudioSegment.empty()

        for idx, part in enumerate(script_parts):
            logger.debug(f"Combining part {idx + 1}/{len(script_parts)}: {part.type}")

            if part.type == ScriptPartType.SPEAK:
                if idx not in speech_map:
                    logger.warning(f"Part {idx + 1} has no generated speech, skipping")
                    continue

                speech_segment = self.pcm_to_audio_segment(speech_map[idx])
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
            f"Combined audio complete (parallel): {len(final_audio)}ms total duration, "
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
