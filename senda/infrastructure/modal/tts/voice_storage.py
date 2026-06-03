from typing import Literal

import modal
from pydantic import BaseModel, field_validator

from .common import (
    VOICE_CONDS_DIR,
    VOICE_PROMPTS_DIR,
    VOICE_VOLUME_MOUNT_DIR,
    app,
    chatterbox_tts_voices_vol,
)


class SyncVoiceRequest(BaseModel):
    voice_slug: str
    reference_wav_b64: str

    @field_validator("voice_slug")
    @classmethod
    def slug_is_safe(cls, v: str) -> str:
        if "/" in v or "\\" in v or ".." in v:
            raise ValueError("voice_slug contains invalid characters")
        return v


class DeleteVoiceRequest(BaseModel):
    voice_slug: str

    @field_validator("voice_slug")
    @classmethod
    def slug_is_safe(cls, v: str) -> str:
        if "/" in v or "\\" in v or ".." in v:
            raise ValueError("voice_slug contains invalid characters")
        return v


class SyncVoiceResponse(BaseModel):
    status: Literal["ok"]
    path: str


class DeleteVoiceResponse(BaseModel):
    status: Literal["ok"]
    deleted: str


fastapi_image = modal.Image.debian_slim(python_version="3.10").pip_install(
    "fastapi[standard]==0.136.3", "pydantic==2.9.2"
)


@app.function(
    image=fastapi_image, volumes={VOICE_VOLUME_MOUNT_DIR: chatterbox_tts_voices_vol}
)
@modal.fastapi_endpoint(method="POST", docs=True, requires_proxy_auth=True)
def sync_voice(request: SyncVoiceRequest) -> SyncVoiceResponse:
    import base64
    import os

    wav_bytes = base64.b64decode(request.reference_wav_b64)

    if not wav_bytes.startswith(b"RIFF"):
        raise ValueError("reference_wav_b64 does not appear to be a valid WAV file")

    target_path = f"{VOICE_PROMPTS_DIR}/{request.voice_slug}.wav"
    os.makedirs(VOICE_PROMPTS_DIR, exist_ok=True)

    with open(target_path, "wb") as f:
        f.write(wav_bytes)

    # Delete existing precomputed conditionals to force recompute
    pt_path = f"{VOICE_CONDS_DIR}/{request.voice_slug}.pt"
    if os.path.exists(pt_path):
        os.remove(pt_path)

    chatterbox_tts_voices_vol.commit()
    return SyncVoiceResponse(status="ok", path=target_path)


@app.function(
    image=fastapi_image, volumes={VOICE_VOLUME_MOUNT_DIR: chatterbox_tts_voices_vol}
)
@modal.fastapi_endpoint(method="DELETE", docs=True, requires_proxy_auth=True)
def delete_voice(request: DeleteVoiceRequest) -> DeleteVoiceResponse:
    import os

    target_path = f"{VOICE_PROMPTS_DIR}/{request.voice_slug}.wav"

    if not os.path.exists(target_path):
        raise FileNotFoundError(f"Voice not found: {target_path}")

    os.remove(target_path)

    # Also delete precomputed conditionals if they exist
    pt_path = f"{VOICE_CONDS_DIR}/{request.voice_slug}.pt"
    if os.path.exists(pt_path):
        os.remove(pt_path)

    chatterbox_tts_voices_vol.commit()
    return DeleteVoiceResponse(status="ok", deleted=target_path)
