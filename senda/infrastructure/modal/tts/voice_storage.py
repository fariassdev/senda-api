import modal

from .common import (
    VOICE_PROMPTS_DIR,
    VOICE_VOLUME_MOUNT_DIR,
    DeleteVoiceRequest,
    DeleteVoiceResponse,
    SyncVoiceRequest,
    SyncVoiceResponse,
    app,
    base_image,
    chatterbox_tts_voices_vol,
)


@app.function(
    image=base_image, volumes={VOICE_VOLUME_MOUNT_DIR: chatterbox_tts_voices_vol}
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

    chatterbox_tts_voices_vol.commit()
    return SyncVoiceResponse(status="ok", path=target_path)


@app.function(
    image=base_image, volumes={VOICE_VOLUME_MOUNT_DIR: chatterbox_tts_voices_vol}
)
@modal.fastapi_endpoint(method="DELETE", docs=True, requires_proxy_auth=True)
def delete_voice(request: DeleteVoiceRequest) -> DeleteVoiceResponse:
    import os

    target_path = f"{VOICE_PROMPTS_DIR}/{request.voice_slug}.wav"

    if not os.path.exists(target_path):
        raise FileNotFoundError(f"Voice not found: {target_path}")

    os.remove(target_path)
    chatterbox_tts_voices_vol.commit()
    return DeleteVoiceResponse(status="ok", deleted=target_path)
