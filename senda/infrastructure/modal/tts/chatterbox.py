import modal
from fastapi.responses import StreamingResponse

from .common import (
    MODEL_DIR,
    VOICE_CONDS_DIR,
    VOICE_PROMPTS_DIR,
    VOICE_VOLUME_MOUNT_DIR,
    TTSRequest,
    app,
    chatterbox_tts_voices_vol,
    chatterbox_tts_weights_vol,
)

tts_image = (
    modal.Image.debian_slim(python_version="3.10")
    .pip_install(
        "chatterbox-tts==0.1.7",
        "fastapi[standard]==0.136.3",
        "peft==0.19.1",
        "pydantic==2.9.2",
    )
    .env({"HF_HOME": "/models"})
)

with tts_image.imports():
    import io
    import os

    import torchaudio as ta
    from chatterbox.tts_turbo import ChatterboxTurboTTS, Conditionals
    from fastapi.responses import StreamingResponse


@app.cls(
    image=tts_image,
    gpu="T4",
    scaledown_window=60 * 5,
    secrets=[modal.Secret.from_name("hf-token")],
    volumes={
        VOICE_VOLUME_MOUNT_DIR: chatterbox_tts_voices_vol,
        MODEL_DIR: chatterbox_tts_weights_vol,
    },
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
    def synthesize(self, request: TTSRequest) -> StreamingResponse:
        print(f"Synthesizing text (voice={request.voice_slug}): {request.text}")
        audio_bytes = self._generate.local(request.text, request.voice_slug)
        return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/wav")

    @modal.method()
    def _generate(self, prompt: str, voice: str) -> bytes:
        """Core generation logic using the Chatterbox model."""
        pt_path = f"{VOICE_CONDS_DIR}/{voice}.pt"
        wav_path = f"{VOICE_PROMPTS_DIR}/{voice}.wav"

        conditionals = None
        if os.path.exists(pt_path):
            print(f"Loading precomputed conditionals: {pt_path}")
            try:
                conditionals = Conditionals.load(pt_path, map_location="cuda")
                if conditionals is None or not isinstance(conditionals, Conditionals):
                    raise ValueError("Loaded conditionals are None or of invalid type")
                self.model.conds = conditionals
            except Exception as e:
                print(
                    f"Error loading conditionals from {pt_path}: {e}. Recomputing from WAV..."
                )
                conditionals = None

        if conditionals is None:
            if os.path.exists(wav_path):
                print(f"Computing conditionals from: {wav_path}")
                self.model.prepare_conditionals(wav_path)
                conditionals = self.model.conds
                if conditionals is not None:
                    conditionals.save(pt_path)
                    chatterbox_tts_voices_vol.commit()
                    print(f"Saved precomputed conditionals to: {pt_path}")
            else:
                raise FileNotFoundError(
                    f"No voice prompt found for '{voice}': expected {pt_path} or {wav_path}"
                )

        wav = self.model.generate(prompt)

        print(
            f"Generated wav tensor: shape={wav.shape}, device={wav.device}, dtype={wav.dtype}"
        )
        print(
            f"Wav stats: min={wav.min().item():.4f}, max={wav.max().item():.4f}, mean={wav.mean().item():.4f}"
        )

        buffer = io.BytesIO()
        ta.save(buffer, wav.cpu(), self.model.sr, format="wav")
        buffer.seek(0)
        return buffer.read()
