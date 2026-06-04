"""Chatterbox voice catalog asset lifecycle on Modal."""

import base64
import logging

import httpx

from senda.core.exceptions import AudioProviderException
from senda.domain.services.audio_generation import IAudioProvider
from senda.domain.services.voice_asset_provisioning import IVoiceAssetProvisioner
from senda.infrastructure.providers.chatterbox_modal import ChatterboxModalSettings

logger = logging.getLogger(__name__)


class ChatterboxVoiceAssetProvisioner(IVoiceAssetProvisioner):
    """Sync and delete voice reference assets on Modal; preview via TTS provider."""

    def __init__(
        self, modal: ChatterboxModalSettings, audio_provider: IAudioProvider
    ) -> None:
        self._modal = modal
        self._audio_provider = audio_provider

    async def sync_reference_voice(self, voice_slug: str, reference_wav: bytes) -> None:
        reference_wav_b64 = base64.b64encode(reference_wav).decode("utf-8")
        payload = {"voice_slug": voice_slug, "reference_wav_b64": reference_wav_b64}

        logger.info(f"Syncing voice '{voice_slug}' WAV to Modal volume")

        try:
            async with httpx.AsyncClient(timeout=self._modal.timeout) as client:
                response = await client.post(
                    self._modal.sync_voice_endpoint,
                    json=payload,
                    headers=self._modal.auth_headers(),
                )
                response.raise_for_status()

            logger.info(f"Voice '{voice_slug}' successfully synced to Modal volume")

        except Exception as e:
            logger.exception(f"Failed to sync voice '{voice_slug}' to Modal: {e}")
            raise AudioProviderException(
                message=f"Modal volume synchronization failed: {str(e)}"
            ) from e

    async def generate_preview_speech(self, text: str, voice_slug: str) -> bytes:
        return await self._audio_provider.generate_speech(
            text=text, voice=voice_slug, speed=1.0
        )

    async def delete_remote_assets(self, voice_slug: str) -> None:
        payload = {"voice_slug": voice_slug}

        logger.info(f"Deleting voice '{voice_slug}' from Modal volume")

        try:
            async with httpx.AsyncClient(timeout=self._modal.timeout) as client:
                response = await client.request(
                    "DELETE",
                    self._modal.delete_voice_endpoint,
                    json=payload,
                    headers=self._modal.auth_headers(),
                )
                response.raise_for_status()

            logger.info(f"Voice '{voice_slug}' removed from Modal volume")

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(
                    f"Voice '{voice_slug}' not found on Modal volume (already deleted)"
                )
                return
            logger.error(
                f"Chatterbox delete HTTP error: {e.response.status_code} - {e.response.text}"
            )
            raise AudioProviderException(
                message=f"Modal volume deletion failed: {e.response.status_code}"
            ) from e
        except Exception as e:
            logger.exception(f"Failed to delete voice '{voice_slug}' from Modal: {e}")
            raise AudioProviderException(
                message=f"Modal volume deletion failed: {str(e)}"
            ) from e
