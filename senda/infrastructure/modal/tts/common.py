import modal

# App & Volume
app = modal.App("senda-tts-chatterbox")
chatterbox_tts_voices_vol = modal.Volume.from_name(
    "chatterbox-tts-voices", create_if_missing=True
)
chatterbox_tts_weights_vol = modal.Volume.from_name(
    "chatterbox-tts-weights", create_if_missing=True
)
VOICE_VOLUME_MOUNT_DIR = "/chatterbox-tts/prompts"
VOICE_PROMPTS_DIR = "/chatterbox-tts/prompts/chatterbox-tts-voices/prompts"
VOICE_CONDS_DIR = "/chatterbox-tts/prompts/chatterbox-tts-voices/voice_conds"
MODEL_DIR = "/models"
