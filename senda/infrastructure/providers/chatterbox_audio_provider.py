import base64
import io
import logging
from typing import Any

import httpx
from pydub import AudioSegment

from senda.core.exceptions import AudioProviderException
from senda.domain.services.audio_generation import IAudioProvider

logger = logging.getLogger(__name__)


class ChatterboxAudioProvider(IAudioProvider):
    """Chatterbox TTS API provider running on Modal.com.

    Generates speech using Chatterbox model via a remote Modal deployment.
    Synchronizes local custom reference voices to the Modal Volume.
    Uses Modal token-based authentication with Basic Auth.
    """

    def __init__(
        self,
        endpoint_url: str,
        token_id: str,
        token_secret: str,
        sync_voice_endpoint: str | None = None,
        delete_voice_endpoint: str | None = None,
        proxy_auth_token_id: str | None = None,
        proxy_auth_token_secret: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        """Initialize the Chatterbox audio provider.

        Args:
            endpoint_url: The Modal synthesize endpoint URL.
            token_id: Modal token ID (ak-xxxxxxxxxxxx).
            token_secret: Modal token secret (as-xxxxxxxxxxxx).
            sync_voice_endpoint: Modal sync_voice endpoint URL (optional).
            delete_voice_endpoint: Modal delete_voice endpoint URL (optional).
            proxy_auth_token_id: Modal proxy auth token ID (wk-xxxxxxxxxxxx) (optional).
            proxy_auth_token_secret: Modal proxy auth token secret (ws-xxxxxxxxxxxx) (optional).
            timeout: HTTP request timeout in seconds.
        """
        self._synthesize_url = endpoint_url.rstrip("/")
        self._sync_voice_url = (
            sync_voice_endpoint.rstrip("/")
            if sync_voice_endpoint
            else self._synthesize_url.replace("/synthesize", "/sync_voice")
        )
        self._delete_voice_url = (
            delete_voice_endpoint.rstrip("/")
            if delete_voice_endpoint
            else self._synthesize_url.replace("/synthesize", "/delete_voice")
        )
        self._token_id = token_id
        self._token_secret = token_secret
        self._proxy_auth_token_id = proxy_auth_token_id
        self._proxy_auth_token_secret = proxy_auth_token_secret
        self._timeout = timeout

        logger.info(
            f"Initialized ChatterboxAudioProvider with synthesize: {self._synthesize_url}"
        )

    def _get_modal_headers(self) -> dict[str, str]:
        """Generate Modal authentication headers.

        Returns:
            Dictionary with headers for Modal token authentication.
        """
        credentials = base64.b64encode(
            f"{self._token_id}:{self._token_secret}".encode()
        ).decode()
        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        }
        if self._proxy_auth_token_id and self._proxy_auth_token_secret:
            headers["Modal-Key"] = self._proxy_auth_token_id
            headers["Modal-Secret"] = self._proxy_auth_token_secret
        return headers

    async def generate_speech(
        self, text: str, voice: str | None = None, speed: float = 1.0
    ) -> bytes:
        """Generate speech audio from text using Chatterbox on Modal.

        Args:
            text: Text to convert to speech.
            voice: Name/slug of the voice to use (defaults to 'Lucy').
            speed: Speech rate multiplier (defaults to 1.0).

        Returns:
            Raw PCM audio bytes resampled to 24kHz mono 16-bit.
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for speech generation")
            raise AudioProviderException(
                message="Cannot generate speech from empty text"
            )

        effective_voice = voice or "Lucy"

        payload = {"text": text, "voice_slug": effective_voice}

        logger.debug(f"Generating Chatterbox speech for voice '{effective_voice}'")

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    self._synthesize_url,
                    json=payload,
                    headers=self._get_modal_headers(),
                )
                response.raise_for_status()
                wav_bytes = response.content

            # Load WAV bytes in pydub and resample to standard 24kHz mono 16-bit PCM
            wav_segment = AudioSegment.from_file(io.BytesIO(wav_bytes), format="wav")
            pcm_segment = (
                wav_segment.set_frame_rate(24000).set_channels(1).set_sample_width(2)
            )

            # Check if speed override is requested
            if speed != 1.0:
                logger.info(
                    f"Applying speed rate multiplier {speed}x to generated audio"
                )
                # Speed up/down segment
                # Note: speedup in pydub can change pitch, or we can use set_frame_rate
                # Let's use simple speedup/slowdown or keep pydub's native set_frame_rate adjustments
                # Pydub speedup is standard
                if speed > 1.0 or speed < 1.0:
                    pcm_segment = pcm_segment.speedup(playback_speed=speed)

            logger.debug(
                f"Successfully resampled Chatterbox output to PCM ({len(pcm_segment.raw_data)} bytes)"
            )
            return pcm_segment.raw_data

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Chatterbox API HTTP error: {e.response.status_code} - {e.response.text}"
            )
            raise AudioProviderException(
                message=f"Chatterbox service returned error: {e.response.status_code}"
            ) from e
        except Exception as e:
            logger.exception(f"Unexpected error in ChatterboxTTS generation: {e}")
            raise AudioProviderException(
                message=f"Chatterbox generation failed: {str(e)}"
            ) from e

    async def sync_voice_to_volume(self, voice_slug: str, reference_wav: bytes) -> None:
        """Upload custom reference WAV file directly to Modal persistent volume."""
        reference_wav_b64 = base64.b64encode(reference_wav).decode("utf-8")

        payload = {"voice_slug": voice_slug, "reference_wav_b64": reference_wav_b64}

        logger.info(f"Syncing voice '{voice_slug}' WAV to Modal Volume")

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    self._sync_voice_url,
                    json=payload,
                    headers=self._get_modal_headers(),
                )
                response.raise_for_status()

            logger.info(f"Voice '{voice_slug}' successfully synced to Modal volume")

        except Exception as e:
            logger.exception(f"Failed to sync voice '{voice_slug}' to Modal: {e}")
            raise AudioProviderException(
                message=f"Modal volume synchronization failed: {str(e)}"
            ) from e

    async def delete_voice_from_volume(self, voice_slug: str) -> None:
        """Remove a voice prompt from the Modal persistent volume."""
        payload = {"voice_slug": voice_slug}

        logger.info(f"Deleting voice '{voice_slug}' from Modal volume")

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.request(
                    "DELETE",
                    self._delete_voice_url,
                    json=payload,
                    headers=self._get_modal_headers(),
                )
                response.raise_for_status()

            logger.info(f"Voice '{voice_slug}' removed from Modal volume")

        except Exception as e:
            logger.exception(f"Failed to delete voice '{voice_slug}' from Modal: {e}")
            raise AudioProviderException(
                message=f"Modal volume deletion failed: {str(e)}"
            ) from e
