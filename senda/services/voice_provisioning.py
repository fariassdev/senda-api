"""External asset provisioning for voice catalog lifecycle.

Creation pipeline (``POST /voices``)
------------------------------------
1. **Remote sync** — write reference WAV to the provider store (e.g. Modal volume).
2. **TTS sample** — synthesize the catalog preview (requires step 1).
3. **S3 reference upload** — ``voices/reference/{slug}.wav``
4. **S3 sample upload** — ``voices/samples/{slug}.mp3``

The database ``INSERT`` is intentionally **last** (in :class:`VoiceService`) so a voice
catalog row exists only when remote, TTS, and S3 are all in a good state.

Deletion pipeline (``DELETE /voices/{voice_id}``)
---------------------------------------------------
1. **Remote delete** — remove provider-specific assets (skipped when no provisioner).
2. **S3 reference delete** — ``voices/reference/{slug}.wav``
3. **S3 sample delete** — ``voices/samples/{slug}.mp3`` (when present)
4. **Database delete** — catalog row (in :class:`VoiceService`)

The catalog row is removed **last** so a ``404`` on retry still means the voice is gone
from the API even if a prior attempt partially cleaned remote/S3 state.

Failure handling
----------------
This is not a two-phase commit across Postgres, remote providers, and S3.

**Create:** Modal and S3 keys are deterministic per ``slug``. Partial artifacts are left
in place; a retry with the same slug overwrites them. No DB row is created until all
steps succeed.

**Delete:** Remote and S3 deletes are idempotent (missing objects are treated as success).
If a step fails before the DB delete, the catalog row remains and the client receives an
error (typically ``502``). A retry continues from the remaining steps because earlier
deletes are safe to repeat.
"""

from dataclasses import dataclass

from senda.domain.services.audio_generation import IStorageProvider
from senda.domain.services.voice_asset_provisioning import IVoiceAssetProvisioner
from senda.infrastructure.utils.audio_processor import AudioProcessor

_PREVIEW_TEMPLATE = (
    "Hello, I am {name}. Take a deep breath, relax, "
    "and let me guide you on your journey to mindfulness with Senda."
)


def reference_s3_key(slug: str) -> str:
    return f"voices/reference/{slug}.wav"


def sample_s3_key(slug: str) -> str:
    return f"voices/samples/{slug}.mp3"


@dataclass(frozen=True)
class ProvisionedVoiceAssets:
    reference_s3_key: str
    sample_s3_key: str


async def provision_voice_assets(
    *,
    slug: str,
    name: str,
    reference_wav: bytes,
    voice_asset_provisioner: IVoiceAssetProvisioner,
    storage_provider: IStorageProvider,
    audio_processor: AudioProcessor,
) -> ProvisionedVoiceAssets:
    """Run remote sync, sample generation, and S3 uploads in order."""
    ref_key = reference_s3_key(slug)
    smp_key = sample_s3_key(slug)

    await voice_asset_provisioner.sync_reference_voice(
        voice_slug=slug, reference_wav=reference_wav
    )

    preview_text = _PREVIEW_TEMPLATE.format(name=name)
    sample_pcm = await voice_asset_provisioner.generate_preview_speech(
        text=preview_text, voice_slug=slug
    )

    sample_segment = audio_processor.pcm_to_audio_segment(sample_pcm)
    sample_mp3 = audio_processor.export_to_mp3(sample_segment)

    await storage_provider.upload_file(
        file_data=reference_wav, key=ref_key, content_type="audio/wav"
    )
    await storage_provider.upload_file(
        file_data=sample_mp3, key=smp_key, content_type="audio/mpeg"
    )

    return ProvisionedVoiceAssets(reference_s3_key=ref_key, sample_s3_key=smp_key)


async def deprovision_voice_assets(
    *,
    voice_slug: str,
    reference_s3_key: str,
    sample_s3_key: str | None,
    voice_asset_provisioner: IVoiceAssetProvisioner | None,
    storage_provider: IStorageProvider,
) -> None:
    """Remove remote and S3 artifacts before the catalog row is deleted."""
    if voice_asset_provisioner is not None:
        await voice_asset_provisioner.delete_remote_assets(voice_slug)

    await storage_provider.delete_file(reference_s3_key)
    if sample_s3_key:
        await storage_provider.delete_file(sample_s3_key)
