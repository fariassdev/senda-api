"""Ports for provider-specific voice asset lifecycle (remote storage, preview TTS)."""

import abc


class IVoiceAssetProvisioner(abc.ABC):
    """Sync reference audio and preview samples to a TTS backend's remote store."""

    @abc.abstractmethod
    async def sync_reference_voice(self, voice_slug: str, reference_wav: bytes) -> None:
        """Upload reference WAV to the provider's remote voice store."""

    @abc.abstractmethod
    async def generate_preview_speech(self, text: str, voice_slug: str) -> bytes:
        """Synthesize preview audio (PCM) for catalog sample generation."""

    @abc.abstractmethod
    async def delete_remote_assets(self, voice_slug: str) -> None:
        """Remove provider-specific remote assets for a voice slug."""
