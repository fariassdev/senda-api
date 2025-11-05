"""Unit tests for audio processor utility."""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydub import AudioSegment

from senda.core.enums import ScriptPartType
from senda.domain.dtos.script_generation import ScriptPartDTO
from senda.infrastructure.utils.audio_processor import AudioProcessor


class TestAudioProcessor:
    """Test suite for AudioProcessor."""

    @pytest.fixture
    def audio_processor(self) -> AudioProcessor:
        """Create an AudioProcessor instance."""
        return AudioProcessor(sample_rate=24000, channels=1, sample_width=2)

    @pytest.fixture
    def mock_pcm_data(self) -> bytes:
        """Generate mock PCM audio data."""
        silence = AudioSegment.silent(duration=1000, frame_rate=24000)
        return silence.raw_data

    @pytest.mark.asyncio
    async def test_initialization(self, audio_processor):
        """Test processor initialization with correct parameters."""
        assert audio_processor._sample_rate == 24000
        assert audio_processor._channels == 1
        assert audio_processor._sample_width == 2

    def test_pcm_to_audio_segment_success(self, audio_processor, mock_pcm_data):
        """Test successful conversion of PCM to AudioSegment."""
        audio_segment = audio_processor.pcm_to_audio_segment(mock_pcm_data)

        assert isinstance(audio_segment, AudioSegment)
        assert audio_segment.frame_rate == 24000
        assert audio_segment.channels == 1
        assert audio_segment.sample_width == 2
        assert len(audio_segment) > 0

    def test_pcm_to_audio_segment_empty_data(self, audio_processor):
        """Test error when PCM data is empty."""
        with pytest.raises(ValueError) as exc_info:
            audio_processor.pcm_to_audio_segment(b"")

        assert "empty" in str(exc_info.value).lower()

    def test_pcm_to_audio_segment_invalid_data(self, audio_processor):
        """Test handling when PCM data is invalid.

        Note: pydub doesn't raise error for invalid PCM, it creates empty audio.
        """
        invalid_pcm = b"not_valid_pcm_data"

        # pydub creates empty (0ms) audio segment for invalid PCM
        result = audio_processor.pcm_to_audio_segment(invalid_pcm)

        assert isinstance(result, AudioSegment)
        # Invalid PCM typically results in very short or zero-length audio
        assert len(result) < 100  # Less than 100ms indicates invalid data

    def test_create_silence_success(self, audio_processor):
        """Test creating silence segment."""
        silence = audio_processor.create_silence(2.5)

        assert isinstance(silence, AudioSegment)
        assert len(silence) == 2500
        assert silence.frame_rate == 24000

    def test_create_silence_zero_duration(self, audio_processor):
        """Test creating silence with zero duration."""
        silence = audio_processor.create_silence(0.0)

        assert isinstance(silence, AudioSegment)
        assert len(silence) == 0

    def test_create_silence_negative_duration(self, audio_processor):
        """Test error when duration is negative."""
        with pytest.raises(ValueError) as exc_info:
            audio_processor.create_silence(-1.0)

        assert "negative" in str(exc_info.value).lower()

    def test_create_silence_large_duration(self, audio_processor):
        """Test creating long silence."""
        silence = audio_processor.create_silence(10.0)

        assert len(silence) == 10000

    @pytest.mark.asyncio
    async def test_combine_script_parts_speak_only(
        self, audio_processor, mock_pcm_data
    ):
        """Test combining script parts with only speak parts."""
        script_parts = [
            ScriptPartDTO(type=ScriptPartType.SPEAK, content="Hello", duration=None),
            ScriptPartDTO(type=ScriptPartType.SPEAK, content="World", duration=None),
        ]

        async def mock_generator(text: str) -> bytes:
            return mock_pcm_data

        result = await audio_processor.combine_script_parts(
            script_parts=script_parts, speech_generator=mock_generator
        )

        assert isinstance(result, AudioSegment)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_combine_script_parts_pause_only(self, audio_processor):
        """Test combining script parts with only pause parts."""
        script_parts = [
            ScriptPartDTO(type=ScriptPartType.PAUSE, content=None, duration=1.0),
            ScriptPartDTO(type=ScriptPartType.PAUSE, content=None, duration=2.0),
        ]

        async def mock_generator(text: str) -> bytes:
            raise AssertionError("Should not call speech generator for pauses")

        result = await audio_processor.combine_script_parts(
            script_parts=script_parts, speech_generator=mock_generator
        )

        assert isinstance(result, AudioSegment)
        assert len(result) == 3000

    @pytest.mark.asyncio
    async def test_combine_script_parts_mixed(self, audio_processor, mock_pcm_data):
        """Test combining script parts with mixed speak and pause."""
        script_parts = [
            ScriptPartDTO(
                type=ScriptPartType.SPEAK, content="Hello world", duration=None
            ),
            ScriptPartDTO(type=ScriptPartType.PAUSE, content=None, duration=1.5),
            ScriptPartDTO(type=ScriptPartType.SPEAK, content="Goodbye", duration=None),
        ]

        async def mock_generator(text: str) -> bytes:
            return mock_pcm_data

        result = await audio_processor.combine_script_parts(
            script_parts=script_parts, speech_generator=mock_generator
        )

        assert isinstance(result, AudioSegment)
        assert len(result) > 1500

    @pytest.mark.asyncio
    async def test_combine_script_parts_empty_list(self, audio_processor):
        """Test error when script parts list is empty."""

        async def mock_generator(text: str) -> bytes:
            return b"mock"

        with pytest.raises(ValueError) as exc_info:
            await audio_processor.combine_script_parts(
                script_parts=[], speech_generator=mock_generator
            )

        assert "no script parts" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_combine_script_parts_skip_empty_content(
        self, audio_processor, mock_pcm_data
    ):
        """Test that parts with empty content are skipped."""
        script_parts = [
            ScriptPartDTO(type=ScriptPartType.SPEAK, content="Valid", duration=None),
            ScriptPartDTO(type=ScriptPartType.SPEAK, content="", duration=None),
            ScriptPartDTO(type=ScriptPartType.SPEAK, content=None, duration=None),
        ]

        call_count = 0

        async def mock_generator(text: str) -> bytes:
            nonlocal call_count
            call_count += 1
            return mock_pcm_data

        result = await audio_processor.combine_script_parts(
            script_parts=script_parts, speech_generator=mock_generator
        )

        assert call_count == 1
        assert isinstance(result, AudioSegment)

    @pytest.mark.asyncio
    async def test_combine_script_parts_skip_invalid_pause(
        self, audio_processor, mock_pcm_data
    ):
        """Test that pause parts with invalid duration are skipped."""
        script_parts = [
            ScriptPartDTO(type=ScriptPartType.SPEAK, content="Hello", duration=None),
            ScriptPartDTO(type=ScriptPartType.PAUSE, content=None, duration=None),
            ScriptPartDTO(type=ScriptPartType.PAUSE, content=None, duration=0),
            ScriptPartDTO(type=ScriptPartType.PAUSE, content=None, duration=-1),
            ScriptPartDTO(type=ScriptPartType.PAUSE, content=None, duration=1.0),
        ]

        async def mock_generator(text: str) -> bytes:
            return mock_pcm_data

        result = await audio_processor.combine_script_parts(
            script_parts=script_parts, speech_generator=mock_generator
        )

        assert isinstance(result, AudioSegment)
        assert len(result) > 1000

    @pytest.mark.asyncio
    async def test_combine_script_parts_unknown_type(
        self, audio_processor, mock_pcm_data
    ):
        """Test handling of unknown script part types (should skip)."""

        class UnknownType:
            pass

        script_parts = [
            ScriptPartDTO(type=ScriptPartType.SPEAK, content="Hello", duration=None),
            ScriptPartDTO(type=UnknownType(), content="Test", duration=None),
        ]

        call_count = 0

        async def mock_generator(text: str) -> bytes:
            nonlocal call_count
            call_count += 1
            return mock_pcm_data

        result = await audio_processor.combine_script_parts(
            script_parts=script_parts, speech_generator=mock_generator
        )

        assert call_count == 1
        assert isinstance(result, AudioSegment)

    def test_export_to_mp3_success(self, audio_processor):
        """Test successful export to MP3."""
        audio = AudioSegment.silent(duration=1000, frame_rate=24000)

        mp3_data = audio_processor.export_to_mp3(audio)

        assert isinstance(mp3_data, bytes)
        assert len(mp3_data) > 0

    def test_export_to_mp3_empty_audio(self, audio_processor):
        """Test error when exporting empty audio."""
        audio = AudioSegment.empty()

        with pytest.raises(ValueError) as exc_info:
            audio_processor.export_to_mp3(audio)

        assert "empty" in str(exc_info.value).lower()

    def test_export_to_mp3_ffmpeg_not_found(self, audio_processor):
        """Test error when ffmpeg is not installed."""
        audio = AudioSegment.silent(duration=1000, frame_rate=24000)

        with patch.object(audio, "export", side_effect=FileNotFoundError("ffmpeg")):
            with pytest.raises(RuntimeError) as exc_info:
                audio_processor.export_to_mp3(audio)

            assert "ffmpeg" in str(exc_info.value).lower()

    def test_export_to_mp3_export_fails(self, audio_processor):
        """Test error when export fails unexpectedly."""
        audio = AudioSegment.silent(duration=1000, frame_rate=24000)

        with patch.object(audio, "export", side_effect=Exception("Export error")):
            with pytest.raises(RuntimeError) as exc_info:
                audio_processor.export_to_mp3(audio)

            assert "export failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_full_workflow(self, audio_processor, mock_pcm_data):
        """Test full workflow: combine parts and export to MP3."""
        script_parts = [
            ScriptPartDTO(type=ScriptPartType.SPEAK, content="Welcome", duration=None),
            ScriptPartDTO(type=ScriptPartType.PAUSE, content=None, duration=0.5),
            ScriptPartDTO(
                type=ScriptPartType.SPEAK, content="to meditation", duration=None
            ),
        ]

        async def mock_generator(text: str) -> bytes:
            return mock_pcm_data

        combined_audio = await audio_processor.combine_script_parts(
            script_parts=script_parts, speech_generator=mock_generator
        )

        mp3_data = audio_processor.export_to_mp3(combined_audio)

        assert isinstance(mp3_data, bytes)
        assert len(mp3_data) > 0
        assert len(combined_audio) > 500
