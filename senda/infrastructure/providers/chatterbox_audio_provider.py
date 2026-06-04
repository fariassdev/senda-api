import io
import logging

import httpx
from pydub import AudioSegment

from senda.core.exceptions import AudioProviderException
from senda.domain.services.audio_generation import IAudioProvider
from senda.infrastructure.providers.chatterbox_modal import ChatterboxModalSettings

logger = logging.getLogger(__name__)


class ChatterboxAudioProvider(IAudioProvider):
    """Chatterbox TTS synthesize provider running on Modal.com."""

    def __init__(self, modal: ChatterboxModalSettings) -> None:
        self._modal = modal
        logger.info(
            "Initialized ChatterboxAudioProvider with synthesize: "
            f"{modal.synthesize_endpoint}"
        )

    async def generate_speech(
        self, text: str, voice: str | None = None, speed: float = 1.0
    ) -> bytes:
        """Generate speech audio from text using Chatterbox on Modal."""
        if not text or not text.strip():
            logger.warning("Empty text provided for speech generation")
            raise AudioProviderException(
                message="Cannot generate speech from empty text"
            )

        if not voice:
            raise AudioProviderException(
                message="Voice slug is required for Chatterbox TTS"
            )

        payload = {"text": text, "voice_slug": voice}
        logger.debug(f"Generating Chatterbox speech for voice '{voice}'")

        try:
            async with httpx.AsyncClient(timeout=self._modal.timeout) as client:
                response = await client.post(
                    self._modal.synthesize_endpoint,
                    json=payload,
                    headers=self._modal.auth_headers(),
                )
                response.raise_for_status()
                wav_bytes = response.content

            wav_segment = AudioSegment.from_file(io.BytesIO(wav_bytes), format="wav")
            pcm_segment = (
                wav_segment.set_frame_rate(24000).set_channels(1).set_sample_width(2)
            )

            if speed != 1.0:
                logger.info(
                    f"Applying speed rate multiplier {speed}x to generated audio"
                )
                pcm_segment = pcm_segment.speedup(playback_speed=speed)

            logger.debug(
                "Successfully resampled Chatterbox output to PCM "
                f"({len(pcm_segment.raw_data)} bytes)"
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
            logger.exception(f"Unexpected error in Chatterbox TTS generation: {e}")
            raise AudioProviderException(
                message=f"Chatterbox generation failed: {str(e)}"
            ) from e
