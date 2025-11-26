"""Unit tests for Kokoro TTS audio provider."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from senda.core.exceptions import AudioProviderException
from senda.infrastructure.providers.kokoro_audio_provider import KokoroAudioProvider


class TestKokoroAudioProvider:
    """Test suite for KokoroAudioProvider."""

    @pytest.fixture
    def audio_provider(self) -> KokoroAudioProvider:
        """Create a KokoroAudioProvider instance."""
        return KokoroAudioProvider(
            api_url="http://localhost:8880/v1/audio/speech",
            model="kokoro",
            voice="af_nicole",
            timeout=30.0,
        )

    @pytest.fixture
    def mock_audio_data(self) -> bytes:
        """Sample PCM audio data."""
        return b"fake_pcm_audio_data" * 100

    @pytest.mark.asyncio
    async def test_initialization(self, audio_provider):
        """Test provider initialization with correct parameters."""
        assert audio_provider._api_url == "http://localhost:8880/v1/audio/speech"
        assert audio_provider._model == "kokoro"
        assert audio_provider._voice == "af_nicole"
        assert audio_provider._timeout == 30.0

    @pytest.mark.asyncio
    async def test_generate_speech_success(self, audio_provider, mock_audio_data):
        """Test successful speech generation."""
        text = "Hello, world! This is a test."

        async def mock_aiter_bytes(chunk_size):
            for i in range(0, len(mock_audio_data), 1024):
                yield mock_audio_data[i : i + 1024]

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_bytes = mock_aiter_bytes

        with patch("httpx.AsyncClient.stream") as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response
            mock_stream.return_value.__aexit__.return_value = None

            result = await audio_provider.generate_speech(text)

            assert result == mock_audio_data
            assert len(result) == len(mock_audio_data)
            mock_stream.assert_called_once_with(
                "POST",
                "http://localhost:8880/v1/audio/speech",
                json={
                    "model": "kokoro",
                    "input": text,
                    "voice": "af_nicole",
                    "response_format": "pcm",
                    "stream": True,
                },
                headers={"Content-Type": "application/json"},
            )

    @pytest.mark.asyncio
    async def test_generate_speech_empty_text(self, audio_provider):
        """Test error when text is empty."""
        with pytest.raises(AudioProviderException) as exc_info:
            await audio_provider.generate_speech("")

        assert "empty text" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_generate_speech_whitespace_only_text(self, audio_provider):
        """Test error when text is only whitespace."""
        with pytest.raises(AudioProviderException) as exc_info:
            await audio_provider.generate_speech("   \n\t  ")

        assert "empty text" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_generate_speech_timeout(self, audio_provider):
        """Test timeout handling."""
        text = "This will timeout"

        with patch("httpx.AsyncClient.stream") as mock_stream:
            mock_stream.side_effect = httpx.TimeoutException("Request timeout")

            with pytest.raises(AudioProviderException) as exc_info:
                await audio_provider.generate_speech(text)

            assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_generate_speech_http_error_404(self, audio_provider):
        """Test HTTP 404 error handling."""
        text = "This will fail with 404"

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )

        with patch("httpx.AsyncClient.stream") as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response
            mock_stream.return_value.__aexit__.return_value = None

            with pytest.raises(AudioProviderException) as exc_info:
                await audio_provider.generate_speech(text)

            assert "404" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_speech_http_error_503(self, audio_provider):
        """Test HTTP 503 service unavailable error."""
        text = "Service unavailable"

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Service Unavailable", request=MagicMock(), response=mock_response
        )

        with patch("httpx.AsyncClient.stream") as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response
            mock_stream.return_value.__aexit__.return_value = None

            with pytest.raises(AudioProviderException) as exc_info:
                await audio_provider.generate_speech(text)

            assert "503" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_speech_connection_error(self, audio_provider):
        """Test connection error handling."""
        text = "Connection will fail"

        with patch("httpx.AsyncClient.stream") as mock_stream:
            mock_stream.side_effect = httpx.ConnectError("Connection refused")

            with pytest.raises(AudioProviderException) as exc_info:
                await audio_provider.generate_speech(text)

            assert "connect" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_generate_speech_unexpected_error(self, audio_provider):
        """Test unexpected error handling."""
        text = "Unexpected error"

        with patch("httpx.AsyncClient.stream") as mock_stream:
            mock_stream.side_effect = ValueError("Unexpected issue")

            with pytest.raises(AudioProviderException) as exc_info:
                await audio_provider.generate_speech(text)

            assert "speech generation failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_generate_speech_empty_chunks(self, audio_provider):
        """Test handling of empty response chunks."""
        text = "Empty chunks test"

        async def mock_aiter_bytes(chunk_size):
            for chunk in [b"", b"", b""]:
                yield chunk

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_bytes = mock_aiter_bytes

        with patch("httpx.AsyncClient.stream") as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response
            mock_stream.return_value.__aexit__.return_value = None

            result = await audio_provider.generate_speech(text)

            # Empty chunks should result in empty audio data
            assert result == b""

    @pytest.mark.asyncio
    async def test_generate_speech_partial_chunks(self, audio_provider):
        """Test combining multiple audio chunks."""
        text = "Multiple chunks test"

        chunk1 = b"chunk1_data"
        chunk2 = b"chunk2_data"
        chunk3 = b"chunk3_data"

        async def mock_aiter_bytes(chunk_size):
            for chunk in [chunk1, chunk2, chunk3]:
                yield chunk

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_bytes = mock_aiter_bytes

        with patch("httpx.AsyncClient.stream") as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response
            mock_stream.return_value.__aexit__.return_value = None

            result = await audio_provider.generate_speech(text)

            assert result == chunk1 + chunk2 + chunk3
            assert len(result) == len(chunk1) + len(chunk2) + len(chunk3)
