# ChatterboxTTS Modal Deployment Guide

This guide covers the initial setup and deployment of ChatterboxTTS on Modal.com.

---

## 1. Prerequisites

- Active account on [modal.com](https://modal.com)
- Project dependencies installed: `make setup"`
- Hugging Face account and token (for model weights download)
- AWS S3 credentials (for audio storage)

---

## 2. Initial Setup

### Step 1: Install and Configure Modal CLI

```bash
# Install project dependencies (includes modal CLI)
make setup

# Authenticate with your Modal account
python3 -m modal setup

# Follow the prompts to create and save your Modal token
# Tokens are stored in ~/.modal/token_cache.json
```

### Step 2: Create Modal Volume for Voices

```bash
# Create the persistent volume for Chatterbox voices
modal volume create chatterbox-tts-voices

# Download ChatterboxTTS demo voices (~100MB)
wget https://modal-cdn.com/blog/audio/chatterbox-tts-voices.zip
unzip chatterbox-tts-voices.zip

# Upload voices to Modal Volume
# The extracted directory contains /prompts with voice .pt files
modal volume put chatterbox-tts-voices chatterbox-tts-voices/prompts /chatterbox-tts/prompts
```

The volume will be mounted at `/chatterbox-tts/prompts` inside containers at runtime.

### Step 2c: Pre-populate Model Weights Volume (Recommended)

To avoid downloading the ~2GB Chatterbox Turbo model weights from Hugging Face on every container startup/cold-start, Senda uses a dedicated cache volume named `chatterbox-tts-weights`.

Although it is automatically created on deployment if missing, you should pre-populate it to avoid a very slow first generation:

```bash
# Download and cache default model weights (ResembleAI/chatterbox-turbo) into the volume
modal run senda.infrastructure.modal.tts.main::download_model

# Optionally, specify a custom Hugging Face repository and revision
modal run senda.infrastructure.modal.tts.main::download_model --repo-id "ResembleAI/chatterbox" --revision "main"
```

This runs a one-time utility function on Modal using a lightweight container image that fetches the weights from Hugging Face and commits them to the volume cache.

### Step 2b: Sync Voices to Database and S3 (After uploading)

Once your voice samples are in the Modal volume, synchronize them to the Senda database and S3 storage.

**First, add your Modal credentials to `.env` (use standard access tokens starting with `ak-`/`as-`):**

```bash
MODAL_TOKEN_ID=ak-xxxxxxxxxxxx
MODAL_TOKEN_SECRET=as-xxxxxxxxxxxx
```

**Then run the sync:**

```bash
# Sync all voices from Modal volume
make sync-voices

# Sync only voices matching a pattern
make sync-voices FILTER=aaron
```

This step:
- Downloads each voice from Modal volume
- Creates a `Voice` record in the database
- Uploads the reference WAV to S3 (`voices/reference/{slug}.wav`)
- Generates and uploads a sample (`voices/samples/{slug}_sample.mp3`)

For detailed instructions and troubleshooting, see [Voice Sync Guide](./VOICE_SYNC_GUIDE.md).

### Step 3: Create Hugging Face Secret

ChatterboxTTS needs access to Hugging Face to download model weights:

**Option A: Via Modal Dashboard (recommended)**
1. Go to [modal.com/settings/secrets](https://modal.com/settings/secrets)
2. Click "Create new secret"
3. Name: `hf-token`
4. Add environment variable: `HF_TOKEN` = your Hugging Face token (get at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens))

**Option B: Via Modal CLI**

```bash
modal secret create hf-token --env HF_TOKEN="hf_yourTokenHere"
```

---

## 3. Deployment

### Step 1: Deploy to Modal

```bash
# Deploy the Chatterbox TTS application to Modal
cd senda-api
modal deploy -m senda.infrastructure.modal.tts.main

# Expected output:
# ✓ Created app 'senda-tts-chatterbox'
# ✓ Created Chatterbox
# ✓ Created sync_voice
# ✓ Created delete_voice
# ✓ API endpoint ready at https://username--senda-tts-chatterbox-synthesize.modal.run
```

### Step 2: Update Environment Variables

After deployment, Modal provides three endpoint URLs. Save them to `.env`:

```bash
# Update your .env with the Modal endpoints
MODAL_TTS_ENDPOINT=https://username--senda-tts-chatterbox-synthesize.modal.run
MODAL_SYNC_VOICE_ENDPOINT=https://username--senda-tts-chatterbox-sync-voice.modal.run
MODAL_DELETE_VOICE_ENDPOINT=https://username--senda-tts-chatterbox-delete-voice.modal.run

# Add your Modal API tokens for authentication
MODAL_TOKEN_ID=ak-xxxxxxxxxxxx
MODAL_TOKEN_SECRET=as-xxxxxxxxxxxx

# Add Proxy Auth tokens for endpoint proxy authorization (starts with `wk-`/`ws-`)
MODAL_PROXY_AUTH_TOKEN_ID=wk-xxxxxxxxxxxx
MODAL_PROXY_AUTH_TOKEN_SECRET=ws-xxxxxxxxxxxx
```

Get your Modal API tokens from [modal.com/settings](https://modal.com/settings) → API Tokens.

---

## 4. Managing Custom Voices

### Upload Custom Voice References

To add custom voice references to the Modal volume:

```bash
# Upload a .wav file as a voice reference
# File will be stored in /chatterbox-tts/prompts with the voice_slug as filename
modal volume put chatterbox-tts-voices local/path/to/voice.wav /chatterbox-tts/prompts/custom-voice-slug.wav

# Verify the upload
modal volume ls chatterbox-tts-voices /chatterbox-tts/prompts/
```

### Sync Voice via API

Once uploaded to the volume, sync the voice through your Senda API:

```bash
# Example: Sync a custom voice from the volume
curl -X POST https://your-senda-api.com/api/v1/audio/voices/sync \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "voice_slug": "custom-voice-slug",
    "reference_wav": "base64_encoded_wav_bytes"
  }'
```

The `sync_voice` Modal endpoint is called internally through the ChatterboxAudioProvider.

---

## 5. Monitoring and Logs

```bash
# View real-time logs from your Modal deployment
modal logs senda-tts-chatterbox

# View logs for a specific function
modal logs senda-tts-chatterbox::Chatterbox.synthesize

# View all your deployments
modal app list

# View app details and usage
modal app info senda-tts-chatterbox

# Dashboard: https://modal.com/apps/senda-tts-chatterbox
```

---

## 6. GPU and Resource Configuration

Modal GPU options are configured in the `@app.cls()` decorator in `chatterbox.py`:

```python
@app.cls(
    image=tts_image,
    gpu="a10g",  # or "h100", "a100", "t4"
    scaledown_window=60 * 5,  # Keep container alive for 5 min of inactivity
    secrets=[modal.Secret.from_name("hf-token")],
    volumes={VOICE_PROMPTS_DIR: chatterbox_tts_voices_vol},
)
```

**Available GPU options:**
- `a10g`: $0.30/hour (good balance, recommended for most workloads)
- `t4`: $0.15/hour (budget option for PoC/development)
- `a100`: $1.00/hour (production, high throughput)
- `h100`: $4.00/hour (maximum performance)

To change GPU, edit `chatterbox.py` and redeploy:

```bash
modal deploy -m senda.infrastructure.modal.tts.main
```

---

## 7. Endpoint Authentication

Endpoints are protected with Modal token-based authentication. Senda supports both:
1. **Basic Auth** using standard access tokens (uses `Authorization` header):
```
Authorization: Basic base64(MODAL_TOKEN_ID:MODAL_TOKEN_SECRET)
```
2. **Proxy Auth** using Proxy Auth Web Credentials (uses custom headers):
```
Modal-Key: MODAL_PROXY_AUTH_TOKEN_ID
Modal-Secret: MODAL_PROXY_AUTH_TOKEN_SECRET
```

The `ChatterboxAudioProvider` automatically handles both methods in `senda/infrastructure/providers/chatterbox_audio_provider.py` by sending Basic Auth headers and, if configured, injecting `Modal-Key` and `Modal-Secret` proxy auth headers.

### Available Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/synthesize` | POST | Generate speech from text |
| `/sync_voice` | POST | Sync custom voice reference to volume |
| `/delete_voice` | DELETE | Remove voice from volume |

All endpoints require `requires_proxy_auth=True` and valid Modal credentials.

---

## 8. Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| `Secret not found` | HF token secret not created | Create with `python3 -m modal secret create hf-token --env HF_TOKEN="..."` |
| `Volume not found` | Volume doesn't exist | Create with `python3 -m modal volume create chatterbox-tts-voices` |
| `Slow first startup` | Weights volume not pre-populated | Run `modal run senda.infrastructure.modal.tts.main::download_model` to pre-cache weights |
| `CUDA out of memory` | Model too large for GPU | Increase GPU tier or reduce concurrent requests |
| `Timeout on requests` | Generation takes >600s | Increase timeout in `chatterbox.py` or reduce text length |
| `401 Unauthorized` | Invalid Modal token credentials | Verify `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`, `MODAL_PROXY_AUTH_TOKEN_ID`, and `MODAL_PROXY_AUTH_TOKEN_SECRET` in `.env` |
| `Connection refused` | Endpoint URL incorrect or down | Check `.env` and redeploy if needed |

---

## 9. Local Development

To test the Modal app locally before deploying:

```bash
# Run locally in development mode (doesn't deploy to Modal cloud)
cd senda-api
modal run -m senda.infrastructure.modal.tts.main

# Run specific function locally
modal run -m senda.infrastructure.modal.tts.chatterbox::Chatterbox.synthesize
```

---

## 10. Pricing and Costs

- **Free tier**: Up to ~50 hours of T4 GPU per month
- **T4**: $0.15/hour
- **A10G**: $0.30/hour
- **A100**: $1.00/hour
- **H100**: $4.00/hour

Monitor usage at [modal.com/pricing](https://modal.com/pricing).

---

## 11. Resources

- [Modal Documentation](https://modal.com/docs)
- [Modal Pricing](https://modal.com/pricing)
- [ChatterboxTTS GitHub](https://github.com/diegoberriosr/ChatterboxTTS)
- [Senda TTS PRD](./senda_tts_prd_modal_chatterbox.md)
- [Architecture Documentation](./architecture-senda-api.md)
