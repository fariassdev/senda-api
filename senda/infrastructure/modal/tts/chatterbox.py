import io

import modal

from .common import (
    VOICE_PROMPTS_DIR,
    VOICE_VOLUME_MOUNT_DIR,
    TTSRequest,
    TTSResponse,
    app,
    chatterbox_tts_voices_vol,
    tts_image,
)

with tts_image.imports():
    import torchaudio as ta
    from chatterbox.tts_turbo import ChatterboxTurboTTS


@app.cls(
    image=tts_image,
    gpu="a10g",
    scaledown_window=60 * 5,  # Keep container alive for 5 minutes of inactivity
    secrets=[modal.Secret.from_name("hf-token")],
    volumes={VOICE_VOLUME_MOUNT_DIR: chatterbox_tts_voices_vol},
    retries=modal.Retries(max_retries=2, backoff_coefficient=2.0, initial_delay=1.0),
)
@modal.concurrent(max_inputs=10)
class Chatterbox:
    @modal.enter()
    def load(self) -> None:
        """Load ChatterboxTurboTTS model into GPU memory once per container startup."""
        print("Loading ChatterboxTurboTTS model...")
        self.model = ChatterboxTurboTTS.from_pretrained(device="cuda")
        print(f"Model loaded. SR: {self.model.sr} Hz")

    @modal.fastapi_endpoint(docs=True, method="POST", requires_proxy_auth=True)
    def synthesize(self, request: TTSRequest) -> TTSResponse:
        import base64

        audio_bytes = self._generate(
            request.text,
            request.voice_slug,
            request.exaggeration,
            request.cfg_weight,
            request.temperature,
        )
        return TTSResponse(
            audio_b64=base64.b64encode(audio_bytes).decode("utf-8"),
            sample_rate=self.model.sr,
        )

    def _generate(
        self,
        prompt: str,
        voice: str,
        exaggeration: float,
        cfg_weight: float,
        temperature: float,
    ) -> bytes:
        """Core generation logic using the Chatterbox model."""
        import os

        voice_path = f"{VOICE_PROMPTS_DIR}/{voice}.wav"
        if not os.path.exists(voice_path):
            raise FileNotFoundError(f"Voice prompt not found: {voice_path}")

        wav = self.model.generate(
            prompt,
            audio_prompt_path=voice_path,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
            temperature=temperature,
        )

        buffer = io.BytesIO()
        ta.save(buffer, wav, self.model.sr, format="wav")
        buffer.seek(0)
        return buffer.read()
