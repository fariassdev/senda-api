"""Chatterbox implementation of voice asset provisioning on Modal."""

from senda.domain.services.voice_asset_provisioning import IVoiceAssetProvisioner
from senda.infrastructure.providers.chatterbox_audio_provider import (
    ChatterboxAudioProvider,
)


class ChatterboxVoiceAssetProvisioner(IVoiceAssetProvisioner):
    """Delegates voice lifecycle operations to :class:`ChatterboxAudioProvider`."""

    def __init__(self, chatterbox_provider: ChatterboxAudioProvider) -> None:
        self._chatterbox = chatterbox_provider

    async def sync_reference_voice(self, voice_slug: str, reference_wav: bytes) -> None:
        await self._chatterbox.sync_voice_to_volume(
            voice_slug=voice_slug, reference_wav=reference_wav
        )

    async def generate_preview_speech(self, text: str, voice_slug: str) -> bytes:
        return await self._chatterbox.generate_speech(
            text=text, voice=voice_slug, speed=1.0
        )

    async def delete_remote_assets(self, voice_slug: str) -> None:
        await self._chatterbox.delete_voice_from_volume(voice_slug)
