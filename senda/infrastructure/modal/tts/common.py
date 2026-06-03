from typing import Literal

import modal
from pydantic import BaseModel, field_validator

# App & Volume
app = modal.App("senda-tts-chatterbox")
chatterbox_tts_voices_vol = modal.Volume.from_name("chatterbox-tts-voices")
chatterbox_tts_weights_vol = modal.Volume.from_name(
    "chatterbox-tts-weights", create_if_missing=True
)
VOICE_VOLUME_MOUNT_DIR = "/chatterbox-tts/prompts"
VOICE_PROMPTS_DIR = "/chatterbox-tts/prompts/chatterbox-tts-voices/prompts"
VOICE_CONDS_DIR = "/chatterbox-tts/prompts/chatterbox-tts-voices/voice_conds"
MODEL_DIR = "/models"


# --- Request schemas ---
class TTSRequest(BaseModel):
    text: str
    voice_slug: str


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


# --- Response schemas ---
class SyncVoiceResponse(BaseModel):
    status: Literal["ok"]
    path: str


class DeleteVoiceResponse(BaseModel):
    status: Literal["ok"]
    deleted: str
