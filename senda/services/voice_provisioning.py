"""External asset provisioning for ``POST /voices``.

Creation pipeline (strict order)
--------------------------------
1. **Modal volume sync** — write ``{slug}.wav`` to the Chatterbox prompts volume.
2. **TTS sample** — synthesize the catalog preview (requires step 1).
3. **S3 reference upload** — ``voices/reference/{slug}.wav``
4. **S3 sample upload** — ``voices/samples/{slug}_sample.mp3``

The database ``INSERT`` is intentionally **last** (in :class:`VoiceService`) so a voice
catalog row exists only when Modal, TTS, and S3 are all in a good state.

Why Modal runs before S3
------------------------
Step 2 calls the remote synthesize endpoint, which reads the reference from Modal.
Syncing Modal first keeps a single linear flow without staging the WAV only in S3.

Failure handling (idempotent compensation)
------------------------------------------
Modal and S3 object keys are deterministic per ``slug``. We do **not** delete partial
artifacts on failure; a retry with the same slug overwrites them.

Effects of a failed request:

- **No DB row** — slug stays free unless a previous run committed (409 on duplicate).
- **Modal / S3** — may contain data for that slug; safe to overwrite on retry.

This is not a two-phase commit across Postgres, Modal, and S3. The catalog row is the
source of truth: clients only treat a voice as created after ``201`` and a committed
transaction that includes the ``INSERT``.
"""

from dataclasses import dataclass

from senda.domain.services.audio_generation import IStorageProvider
from senda.infrastructure.providers.chatterbox_audio_provider import (
    ChatterboxAudioProvider,
)
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
    chatterbox_provider: ChatterboxAudioProvider,
    storage_provider: IStorageProvider,
    audio_processor: AudioProcessor,
) -> ProvisionedVoiceAssets:
    """Run Modal sync, sample generation, and S3 uploads in order."""
    ref_key = reference_s3_key(slug)
    smp_key = sample_s3_key(slug)

    await chatterbox_provider.sync_voice_to_volume(
        voice_slug=slug, reference_wav=reference_wav
    )

    preview_text = _PREVIEW_TEMPLATE.format(name=name)
    sample_pcm = await chatterbox_provider.generate_speech(
        text=preview_text, voice=slug, speed=1.0
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
