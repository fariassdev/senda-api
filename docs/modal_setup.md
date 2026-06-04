# Chatterbox on Modal — setup

Deploy the TTS app in `senda/infrastructure/modal/tts/` and wire the returned URLs into the Senda API.

## Prerequisites

- [Modal](https://modal.com) account and CLI (`make setup` installs it)
- Hugging Face token (model weights)
- AWS credentials for S3 (configured in the API, not in Modal)

## One-time Modal setup

```bash
# Authenticate
python -m modal setup

# Voice prompts volume (reference WAVs mounted at runtime)
modal volume create chatterbox-tts-voices

# Optional: seed demo prompts (or skip and use POST /voices only)
wget https://modal-cdn.com/blog/audio/chatterbox-tts-voices.zip
unzip chatterbox-tts-voices.zip
modal volume put chatterbox-tts-voices chatterbox-tts-voices/prompts /chatterbox-tts/prompts

# Pre-cache model weights (~2GB) to avoid slow cold starts
modal run -m senda.infrastructure.modal.tts.main::download_model

# Hugging Face secret for weight download inside containers
modal secret create hf-token --env HF_TOKEN="hf_..."
```

Weights use volume `chatterbox-tts-weights` (created on first deploy if missing).

## Deploy

```bash
cd senda-api
modal deploy -m senda.infrastructure.modal.tts.main
```

Note the three endpoint URLs from the deploy output and set in `.env`:

```bash
MODAL_TTS_ENDPOINT=https://...-synthesize.modal.run
MODAL_SYNC_VOICE_ENDPOINT=https://...-sync-voice.modal.run
MODAL_DELETE_VOICE_ENDPOINT=https://...-delete-voice.modal.run
MODAL_TOKEN_ID=ak-...
MODAL_TOKEN_SECRET=as-...
MODAL_PROXY_AUTH_TOKEN_ID=wk-...    # if using proxy auth
MODAL_PROXY_AUTH_TOKEN_SECRET=ws-...
```

Tokens: [modal.com/settings](https://modal.com/settings) → API Tokens.

## Register voices

Use the **Senda admin API**, not manual volume uploads, for catalog voices:

```http
POST /voices
Content-Type: multipart/form-data

reference_wav=<file>
name, slug, gender, language, tts_provider=chatterbox, ...
```

The API syncs Modal, generates a sample, uploads S3 objects, then inserts the DB row. See [chatterbox-tts.md](./chatterbox-tts.md) and `senda/services/voice_provisioning.py`.

## Modal endpoints (internal)

| Endpoint | Method | Called by |
|----------|--------|-----------|
| `/synthesize` | POST | `ChatterboxAudioProvider` |
| `/sync_voice` | POST | `ChatterboxVoiceAssetProvisioner` |
| `/delete_voice` | DELETE | `ChatterboxVoiceAssetProvisioner` |

Auth: Basic `MODAL_TOKEN_ID:MODAL_TOKEN_SECRET`, plus optional `Modal-Key` / `Modal-Secret` headers (`ChatterboxModalSettings.auth_headers()`).

## Operations

```bash
modal logs senda-tts-chatterbox
modal app info senda-tts-chatterbox
```

GPU tier is set in `senda/infrastructure/modal/tts/chatterbox.py` (`gpu="T4"` by default). Change and redeploy if needed.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Secret not found` | Create `hf-token` secret with `HF_TOKEN` |
| `Volume not found` | `modal volume create chatterbox-tts-voices` |
| Slow first synthesis | Run `download_model` to populate weights volume |
| `401 Unauthorized` | Check Modal token and proxy auth env vars |
| Wrong endpoint | Redeploy and update `.env` URLs |

## References

- [chatterbox-tts.md](./chatterbox-tts.md) — architecture and API overview
- [Modal docs](https://modal.com/docs)
