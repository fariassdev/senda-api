# Chatterbox TTS

Senda uses **Chatterbox** (GPU on [Modal.com](https://modal.com)) as the primary TTS engine and **Kokoro** as an optional CPU fallback. Both implement `IAudioProvider`; lesson audio generation selects the engine from the catalog voice's `tts_provider`.

## Components

| Layer | Responsibility |
|-------|----------------|
| `ChatterboxAudioProvider` | Lesson/preview synthesis (`POST /synthesize`) |
| `ChatterboxVoiceAssetProvisioner` | Voice reference sync and delete on Modal |
| `AudioGenerationService` | Parallel TTS per script part, local MP3 composition |
| `VoiceService` + `voice_provisioning` | Admin voice catalog lifecycle |
| Modal app (`senda/infrastructure/modal/tts/`) | GPU inference, volume-backed prompts |

## Voice catalog (admin)

Register voices with **`POST /voices`** (multipart: `reference_wav` + metadata). Pipeline order and retry semantics are documented in `senda/services/voice_provisioning.py`:

1. Modal volume sync (`{slug}.wav`)
2. TTS preview sample
3. S3 reference upload (`voices/reference/{slug}.wav`)
4. S3 sample upload (`voices/samples/{slug}.mp3`)
5. Database insert (last — row exists only when all steps succeed)

Remove with **`DELETE /voices/{voice_id}`** (409 if any lesson references the voice). External cleanup runs before the DB row is deleted; see `deprovision_voice_assets()` in the same module.

## Lesson audio

Audio generation requires **`audio_config.voice_id`** (active catalog voice). The service resolves `tts_provider` → `IAudioProvider`, generates speak parts in parallel, combines with pauses via `AudioProcessor`, and uploads MP3 to S3.

Batch course generation uses **one DB session per lesson** to avoid sharing an async session across concurrent tasks.

## S3 layout

```
{AWS_S3_BUCKET}/
├── voices/reference/{slug}.wav   # catalog reference (admin)
├── voices/samples/{slug}.mp3     # catalog preview (admin)
└── audio/                        # generated lesson MP3s
```

## Environment variables

See `.env.example`. Required for Chatterbox in production:

| Variable | Purpose |
|----------|---------|
| `MODAL_TTS_ENDPOINT` | Synthesize endpoint URL |
| `MODAL_SYNC_VOICE_ENDPOINT` | Sync reference WAV to Modal volume |
| `MODAL_DELETE_VOICE_ENDPOINT` | Remove voice from Modal volume |
| `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET` | Modal API auth (Basic) |
| `MODAL_PROXY_AUTH_TOKEN_ID` / `MODAL_PROXY_AUTH_TOKEN_SECRET` | Modal proxy auth (optional) |
| `AWS_S3_BUCKET`, `AWS_REGION` | Audio and voice asset storage |

## Modal deployment

Operational setup (CLI, volumes, weights cache, deploy, troubleshooting): **[modal_setup.md](./modal_setup.md)**.
