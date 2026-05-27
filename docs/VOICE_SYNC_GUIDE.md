# Voice Sync Guide

This guide covers synchronizing voice samples from Modal volume to the Senda database and S3 storage.

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Workflow](#workflow)
- [Usage](#usage)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

---

## Overview

The voice synchronization process automates the workflow of registering voice samples that have been uploaded to the Modal volume. For each voice, the sync script:

1. Downloads the `.wav` file from the Modal volume
2. Creates a `Voice` record in the database
3. Uploads the reference WAV to S3 at `voices/reference/{slug}.wav`
4. Generates a synthesized audio sample
5. Uploads the sample to S3 at `voices/samples/{slug}_sample.mp3`
6. Marks the voice as `is_synced_to_modal=True` in the database

---

## Prerequisites

Before synchronizing voices, ensure you have:

1. Voice `.wav` files already uploaded to the Modal volume
   - See [modal_setup.md](./modal_setup.md) for upload instructions
2. Modal API credentials
   - Token ID (starts with `ak-`)
   - Token Secret (starts with `as-`)
3. AWS S3 credentials configured in `.env`
4. Database running and accessible
5. Modal CLI installed: `uv pip install modal` or included in project setup

### Get Modal Credentials

1. Navigate to [modal.com/settings](https://modal.com/settings)
2. Go to "API Tokens" section
3. Create or copy existing token credentials

### Configure Credentials

Add your Modal credentials to `.env` file in the senda-api directory (use standard access tokens starting with `ak-`/`as-`):

```bash
# .env
MODAL_TOKEN_ID=ak-xxxxxxxxxxxx
MODAL_TOKEN_SECRET=as-xxxxxxxxxxxx

# Optional: Add Proxy Auth tokens if proxy authentication is enabled on the endpoints (starts with `wk-`/`ws-`)
MODAL_PROXY_AUTH_TOKEN_ID=wk-xxxxxxxxxxxx
MODAL_PROXY_AUTH_TOKEN_SECRET=ws-xxxxxxxxxxxx
```

The sync script will automatically load these credentials from the `.env` file.

---

## Workflow

The voice sync process follows this sequence for each voice in your Modal volume:

```
Modal Volume (.wav)
       ↓
Download to memory
       ↓
Create Voice record in database
       ↓
Upload reference to S3 (voices/reference/)
       ↓
Generate audio sample via Chatterbox TTS
       ↓
Upload sample to S3 (voices/samples/)
       ↓
Update Voice record (is_synced_to_modal=True)
```

If sample generation fails, the voice is still created with the reference file, and the error is logged.

---

## Usage

### Prerequisites

Ensure your `.env` file contains Modal credentials:

```bash
MODAL_TOKEN_ID=ak-xxxxxxxxxxxx
MODAL_TOKEN_SECRET=as-xxxxxxxxxxxx
MODAL_PROXY_AUTH_TOKEN_ID=wk-xxxxxxxxxxxx
MODAL_PROXY_AUTH_TOKEN_SECRET=ws-xxxxxxxxxxxx
```

### Basic Synchronization

Synchronize all voices from your Modal volume:

```bash
make sync-voices
```

### Filter Voices

Synchronize only voices matching a specific pattern:

```bash
make sync-voices FILTER=aaron
```

This will sync only voices containing "aaron" in their filename.

### Manual Execution

You can also run the sync script directly:

```bash
uv run -m senda.management.sync_voices_from_modal
uv run -m senda.management.sync_voices_from_modal --filter aaron
```

### Expected Output

```
=== Modal Voice Sync Started ===
Listing voices from Modal volume...
Found 5 voices in Modal: ['Aaron', 'Lucy', 'Madison', 'Walter', 'Dylan']
Syncing 5 voices...
Downloading Aaron.wav from Modal...
Syncing voice: Aaron
Uploading Aaron reference to S3: voices/reference/Aaron.wav
Created Voice record in database: <UUID>
Generating sample for Aaron...
Uploading sample to S3: voices/samples/Aaron_sample.mp3
Successfully synced voice: Aaron
... (repeats for each voice)
=== Sync Complete ===
Synced: 5
Failed: 0
```

---

## Verification

After running the sync script, verify that all voices were properly synchronized.

### Check Database

Query the voices table to confirm records were created:

```bash
# Connect to database
psql $DATABASE_URL

# List all synced voices
SELECT slug, name, is_synced_to_modal, reference_s3_key, sample_s3_key
FROM voices
ORDER BY created_at DESC;
```

Expected output shows all voices with `is_synced_to_modal = true`.

### Check S3 Storage

Verify that voice files were uploaded to S3:

```bash
# List reference files
aws s3 ls s3://your-bucket/voices/reference/

# List sample files
aws s3 ls s3://your-bucket/voices/samples/
```

### Test API Endpoint

Once voices are synchronized, list them via the API:

```bash
curl http://localhost:8000/api/v1/voices \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Test Audio Generation

Generate audio using a synced voice:

```bash
curl -X POST http://localhost:8000/api/v1/audio/generate \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is a test of the voice synthesis system.",
    "voice_slug": "aaron"
  }'
```

---

## Troubleshooting

### Missing Modal Credentials

**Error:** `MODAL_TOKEN_ID not provided and not found in .env`

**Solution:** Add your Modal credentials to `.env`:

```bash
# .env
MODAL_TOKEN_ID=ak-xxxxxxxxxxxx
MODAL_TOKEN_SECRET=as-xxxxxxxxxxxx
MODAL_PROXY_AUTH_TOKEN_ID=wk-xxxxxxxxxxxx
MODAL_PROXY_AUTH_TOKEN_SECRET=ws-xxxxxxxxxxxx
```

**Error:** `modal: command not found`

**Solution:** Ensure Modal CLI is installed:

```bash
make setup
```

Or manually:

```bash
pip install modal
modal setup
```

### Voice Already Exists

**Error:** `Voice {slug} already exists in database, skipping...`

**Reason:** The script detected an existing voice record with the same slug.

**Solution:** This is expected if running the script multiple times. To re-sync:

1. Delete the voice record from database:
   ```bash
   psql $DATABASE_URL -c "DELETE FROM voices WHERE slug = 'aaron';"
   ```
2. Re-run the sync script

### Failed to Generate Sample

**Error:** `Error generating sample for {voice}: ...`

**Reason:** The Chatterbox TTS API failed to generate the sample audio, possibly due to:
- Chatterbox service not running
- Modal endpoint not responding
- Invalid voice reference file

**Solution:**
- The voice is still created with the reference file
- Check logs for detailed error message
- Verify Chatterbox is deployed: `modal app list`
- Manually generate sample later by running the creation endpoint directly

### Connection Refused / S3 Error

**Error:** `Connection refused` or `Access Denied` from S3

**Solution:** Verify your environment:

1. Check S3 credentials in `.env`:
   ```bash
   echo $AWS_ACCESS_KEY_ID
   echo $AWS_S3_BUCKET
   ```

2. Verify database is running:
   ```bash
   make runserver
   ```

3. Check Modal endpoints are configured:
   ```bash
   grep MODAL_ .env
   ```

### Partial Sync Failure

**Scenario:** Some voices synced successfully, others failed

**Solution:**
- Run sync again with `--filter` to retry failed voices
- Check logs for specific error messages
- Verify individual voice files exist in Modal volume:
  ```bash
  modal volume ls chatterbox-tts-voices /chatterbox-tts/prompts/
  ```

---

## Next Steps

After voices are synchronized and verified:

1. **Refine Voice Metadata** in the database:
   - Set `gender` to 'female', 'male', or 'neutral'
   - Update `description` with voice characteristics
   - Adjust Chatterbox parameters (`exaggeration`, `cfg_weight`, `temperature`)

   ```bash
   psql $DATABASE_URL -c "UPDATE voices
     SET gender = 'male', description = 'Deep male voice'
     WHERE slug = 'aaron';"
   ```

2. **Assign Voices to Lessons** via CMS or database:
   - Link voices to lesson content
   - Set as default voice for new lessons
   - Test audio generation in lessons

3. **Monitor Usage** with Modal dashboard:
   - Track TTS generation requests
   - Monitor GPU usage and costs
   - Review logs at https://modal.com/apps
