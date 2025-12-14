"""Kokoro TTS provider implementation for text-to-speech generation."""

import logging
from typing import Any

import httpx

from senda.core.exceptions import AudioProviderException
from senda.domain.services.audio_generation import IAudioProvider

logger = logging.getLogger(__name__)


class KokoroAudioProvider(IAudioProvider):
    """Kokoro TTS API provider for generating speech audio from text.

    This provider interfaces with a local Kokoro TTS API service to convert
    text into PCM audio data. The service is expected to be running locally
    on the configured URL (default: http://localhost:8880/v1/audio/speech).

    Audio specifications:
    - Format: PCM (raw audio)
    - Sample rate: 24kHz
    - Channels: 1 (mono)
    - Sample width: 2 bytes (16-bit)
    """

    def __init__(
        self,
        api_url: str = "http://localhost:8880/v1/audio/speech",
        model: str = "kokoro",
        voice: str = "af_nicole",
        timeout: float = 30.0,
    ) -> None:
        """Initialize the Kokoro audio provider.

        Args:
            api_url: Base URL for the Kokoro TTS API
            model: Model name to use for TTS
            voice: Voice model to use for speech generation
            timeout: Request timeout in seconds
        """
        self._api_url = api_url
        self._model = model
        self._voice = voice
        self._timeout = timeout

        logger.info(
            f"Initialized KokoroAudioProvider with model={model}, voice={voice}"
        )

    async def generate_speech(
        self, text: str, voice: str | None = None, speed: float = 1.0
    ) -> bytes:
        """Generate speech audio from text using Kokoro TTS API.

        Args:
            text: Text to convert to speech
            voice: Optional voice override (uses instance default if None)
            speed: Speech rate multiplier (0.5 to 2.0, default 1.0)

        Returns:
            Raw PCM audio bytes

        Raises:
            AudioProviderException: If TTS generation fails
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for speech generation")
            raise AudioProviderException(
                message="Cannot generate speech from empty text"
            )

        # Use provided voice or fall back to instance default
        effective_voice = voice or self._voice

        payload: dict[str, Any] = {
            "model": self._model,
            "input": text,
            "voice": effective_voice,
            "response_format": "pcm",
            "stream": True,
            "speed": speed,
        }

        headers = {"Content-Type": "application/json"}

        logger.debug(f"Generating speech for text (length: {len(text)} chars)")

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream(
                    "POST", self._api_url, json=payload, headers=headers
                ) as response:
                    response.raise_for_status()

                    audio_chunks: list[bytes] = []
                    async for chunk in response.aiter_bytes(chunk_size=1024):
                        if chunk:
                            audio_chunks.append(chunk)

                    audio_data = b"".join(audio_chunks)
                    logger.debug(
                        f"Successfully generated speech audio ({len(audio_data)} bytes)"
                    )
                    return audio_data

        except httpx.TimeoutException as e:
            logger.error(f"Kokoro TTS API timeout: {e}")
            raise AudioProviderException(
                message="TTS service timeout - request took too long"
            ) from e

        except httpx.HTTPStatusError as e:
            logger.error(f"Kokoro TTS API HTTP error: {e.response.status_code} - {e}")
            raise AudioProviderException(
                message=f"TTS service returned error: {e.response.status_code}"
            ) from e

        except httpx.RequestError as e:
            logger.error(f"Kokoro TTS API request error: {e}")
            raise AudioProviderException(
                message="Failed to connect to TTS service"
            ) from e

        except Exception as e:
            logger.exception(f"Unexpected error during speech generation: {e}")
            raise AudioProviderException(
                message=f"Speech generation failed: {str(e)}"
            ) from e
