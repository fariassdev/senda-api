from typing import Literal

import modal
from pydantic import BaseModel, field_validator

# Images
tts_image = modal.Image.debian_slim(python_version="3.10").pip_install(
    "chatterbox-tts==0.1.7",
    "fastapi[standard]==0.136.3",
    "peft==0.19.1",
    "pydantic==2.9.2",
)

base_image = modal.Image.debian_slim(python_version="3.10").pip_install(
    "fastapi[standard]==0.136.3", "pydantic==2.9.2"
)

# App & Volume
app = modal.App("senda-tts-chatterbox")
chatterbox_tts_voices_vol = modal.Volume.from_name("chatterbox-tts-voices")
VOICE_VOLUME_MOUNT_DIR = "/chatterbox-tts/prompts"
VOICE_PROMPTS_DIR = "/chatterbox-tts/prompts/chatterbox-tts-voices/prompts"


# --- Request schemas ---


class TTSRequest(BaseModel):
    text: str
    voice_slug: str
    exaggeration: float = 0.3
    cfg_weight: float = 0.5
    temperature: float = 0.4


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


class TTSResponse(BaseModel):
    audio_b64: str
    sample_rate: int


class SyncVoiceResponse(BaseModel):
    status: Literal["ok"]
    path: str


class DeleteVoiceResponse(BaseModel):
    status: Literal["ok"]
    deleted: str
