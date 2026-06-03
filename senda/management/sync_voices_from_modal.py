#!/usr/bin/env python3
"""
Management script to sync voice samples from Modal volume to Senda database and S3.

Usage:
    make sync-voices
    make sync-voices FILTER=aaron

Or manually:
    uv run -m senda.management.sync_voices_from_modal
    uv run -m senda.management.sync_voices_from_modal --filter aaron

This script:
1. Lists all .wav files in Modal volume (/chatterbox-tts/prompts)
2. Creates Voice records in database
3. Downloads voice references and uploads to S3
4. Generates voice samples
5. Updates sync status in database

Modal credentials are read from .env file (MODAL_TOKEN_ID, MODAL_TOKEN_SECRET)
or can be overridden via CLI arguments.
"""

import argparse
import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from senda.core.config import get_app_settings
from senda.core.container import Container
from senda.domain.dtos.voice import CreateVoiceDTO, GenderEnum, UpdateVoiceDTO
from senda.infrastructure.models import Voice

# Configure logging FIRST (before any logger usage)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
# Look for .env in current directory, parent, and project root
env_paths = [
    Path(".env"),
    Path("../.env"),
    Path("../../.env"),
    Path(os.path.expanduser("~/.env.senda")),
]

for env_path in env_paths:
    if env_path.exists():
        logger.info(f"Loading environment from {env_path.resolve()}")
        load_dotenv(env_path)
        break
else:
    # Try default load_dotenv which searches current directory
    load_dotenv()


def validate_modal_credentials(token_id: str | None, token_secret: str | None) -> None:
    """Validate that Modal credentials are provided and not empty.

    Args:
        token_id: Modal token ID
        token_secret: Modal token secret

    Raises:
        ValueError: If credentials are missing or empty
    """
    if not token_id:
        logger.error(
            "MODAL_TOKEN_ID not configured. Please add to .env:\n"
            "  MODAL_TOKEN_ID=ak-xxxxxxxxxxxx"
        )
        raise ValueError("MODAL_TOKEN_ID not configured")

    if not token_secret:
        logger.error(
            "MODAL_TOKEN_SECRET not configured. Please add to .env:\n"
            "  MODAL_TOKEN_SECRET=as-xxxxxxxxxxxx"
        )
        raise ValueError("MODAL_TOKEN_SECRET not configured")

    if not token_id.startswith("ak-"):
        logger.error(f"MODAL_TOKEN_ID appears invalid: {token_id[:10]}...")
        raise ValueError("MODAL_TOKEN_ID format is invalid (should start with 'ak-')")

    if not token_secret.startswith("as-"):
        logger.error(f"MODAL_TOKEN_SECRET appears invalid: {token_secret[:10]}...")
        raise ValueError(
            "MODAL_TOKEN_SECRET format is invalid (should start with 'as-')"
        )


async def list_modal_voices(modal_token_id: str, modal_token_secret: str) -> list[str]:
    """List all .wav files in Modal volume.

    Uses the `modal volume ls` command to list files in the volume.

    Args:
        modal_token_id: Modal API token ID
        modal_token_secret: Modal API token secret

    Returns:
        List of voice slugs (filenames without .wav extension)
    """
    logger.info("Listing voices from Modal volume...")

    try:
        # Use asyncio subprocess to avoid event loop conflicts on Windows
        process = await asyncio.create_subprocess_exec(
            "modal",
            "volume",
            "ls",
            "chatterbox-tts-voices",
            "/chatterbox-tts-voices/prompts",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={
                **os.environ,
                "MODAL_TOKEN_ID": modal_token_id,
                "MODAL_TOKEN_SECRET": modal_token_secret,
                "PYTHONIOENCODING": "utf-8",
                "PYTHONUTF8": "1",
            },
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"Modal CLI error: {stderr.decode('utf-8', errors='replace')}")
            raise RuntimeError(
                f"Failed to list Modal volume: {stderr.decode('utf-8', errors='replace')}"
            )

        # Parse output lines to extract filenames
        voices = []
        for line in stdout.decode("utf-8", errors="replace").split("\n"):
            line = line.strip()
            if line.endswith(".wav"):
                # Extract filename from output
                filename = line.split()[-1] if " " in line else line
                if filename.endswith(".wav"):
                    basename = os.path.basename(filename)
                    slug = basename[:-4]  # Remove .wav extension
                    voices.append(slug)

        logger.info(f"Found {len(voices)} voices in Modal: {voices}")
        return voices

    except Exception as e:
        logger.error(f"Error listing Modal voices: {e}")
        raise


async def download_voice_from_modal(
    modal_token_id: str, modal_token_secret: str, voice_slug: str
) -> bytes:
    """Download a voice file from Modal volume.

    Args:
        modal_token_id: Modal API token ID
        modal_token_secret: Modal API token secret
        voice_slug: Voice slug/filename (without .wav)

    Returns:
        Voice audio bytes
    """
    logger.info(f"Downloading {voice_slug}.wav from Modal...")

    try:
        # Use asyncio subprocess to avoid event loop conflicts on Windows
        process = await asyncio.create_subprocess_exec(
            "modal",
            "volume",
            "get",
            "chatterbox-tts-voices",
            f"/chatterbox-tts-voices/prompts/{voice_slug}.wav",
            "-",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={
                **os.environ,
                "MODAL_TOKEN_ID": modal_token_id,
                "MODAL_TOKEN_SECRET": modal_token_secret,
                "PYTHONIOENCODING": "utf-8",
                "PYTHONUTF8": "1",
            },
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(
                f"Failed to download {voice_slug}.wav: {stderr.decode('utf-8', errors='replace')}"
            )

        return stdout

    except Exception as e:
        logger.error(f"Error downloading voice from Modal: {e}")
        raise


async def sync_voice(
    container: Container,
    session: AsyncSession,
    voice_slug: str,
    reference_wav: bytes,
    force: bool = False,
) -> bool:
    """Synchronize a single voice from Modal to database and S3.

    Args:
        container: Dependency container
        session: Database session
        voice_slug: Voice slug/identifier
        reference_wav: Voice audio bytes
        force: Whether to force sync/regeneration for existing voices

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Syncing voice: {voice_slug}")

        # Check if voice already exists
        stmt = select(Voice).where(Voice.slug == voice_slug)
        existing = await session.execute(stmt)
        existing_voice = existing.scalar_one_or_none()

        if existing_voice and not force:
            logger.info(f"Voice {voice_slug} already exists in database, skipping...")
            return True

        # Step 1: Upload reference WAV to S3
        storage_provider = container.storage_provider()
        reference_s3_key = f"voices/reference/{voice_slug}.wav"

        logger.info(f"Uploading {voice_slug} reference to S3: {reference_s3_key}")
        await storage_provider.upload_file(
            file_data=reference_wav, key=reference_s3_key, content_type="audio/wav"
        )

        voice_repo = container.voice_repository()
        voice_name = existing_voice.name if existing_voice else voice_slug.title()

        chatterbox_provider = container.chatterbox_provider()
        preview_text = (
            f"Hello, I am {voice_name}. Take a deep breath, relax, "
            f"and let me guide you on your journey to mindfulness with Senda."
        )

        logger.info(f"Generating sample for {voice_slug}...")
        sample_pcm = await chatterbox_provider.generate_speech(
            text=preview_text, voice=voice_slug, speed=1.0
        )

        audio_processor = container.audio_processor()
        sample_segment = audio_processor.pcm_to_audio_segment(sample_pcm)
        sample_mp3 = audio_processor.export_to_mp3(sample_segment)
        sample_s3_key = f"voices/samples/{voice_slug}_sample.mp3"

        logger.info(f"Uploading sample to S3: {sample_s3_key}")
        await storage_provider.upload_file(
            file_data=sample_mp3, key=sample_s3_key, content_type="audio/mpeg"
        )

        if existing_voice:
            await voice_repo.update(
                session=session,
                voice_id=existing_voice.id,
                update_item=UpdateVoiceDTO(sample_s3_key=sample_s3_key),
            )
        else:
            create_dto = CreateVoiceDTO(
                name=voice_slug.title(),
                slug=voice_slug,
                description=f"Voice synced from Modal: {voice_slug}",
                language="en",
                gender=GenderEnum.NEUTRAL,
                tts_provider="chatterbox",
            )
            await voice_repo.add(
                session=session,
                create_item=create_dto,
                reference_s3_key=reference_s3_key,
                sample_s3_key=sample_s3_key,
            )

        logger.info(f"✓ Successfully synced voice: {voice_slug}")
        return True

    except Exception as e:
        logger.error(f"✗ Failed to sync voice {voice_slug}: {e}")
        return False


async def main(
    modal_token_id: str,
    modal_token_secret: str,
    voice_filter: str | None = None,
    force: bool = False,
) -> None:
    """Main sync function.

    Args:
        modal_token_id: Modal API token ID
        modal_token_secret: Modal API token secret
        voice_filter: Optional filter to sync only voices matching this pattern
        force: Whether to force sync/regeneration for existing voices
    """
    logger.info("=== Modal Voice Sync Started ===")

    # Load app settings
    settings = get_app_settings()

    # Initialize container
    container = Container(settings=settings)

    # List voices in Modal
    modal_voices = await list_modal_voices(modal_token_id, modal_token_secret)

    if not modal_voices:
        logger.warning("No voices found in Modal volume!")
        return

    # Filter if needed
    if voice_filter:
        modal_voices = [v for v in modal_voices if voice_filter.lower() in v.lower()]
        logger.info(f"Filtered to {len(modal_voices)} voices matching '{voice_filter}'")

    logger.info(f"Syncing {len(modal_voices)} voices...")

    # Get database session
    async with container.context_session() as session:
        synced_count = 0
        failed_count = 0

        for voice_slug in modal_voices:
            try:
                # Download voice from Modal
                reference_wav = await download_voice_from_modal(
                    modal_token_id, modal_token_secret, voice_slug
                )

                # Sync to database and S3
                success = await sync_voice(
                    container, session, voice_slug, reference_wav, force=force
                )

                if success:
                    synced_count += 1
                else:
                    failed_count += 1

            except Exception as e:
                logger.error(f"Error processing {voice_slug}: {e}")
                failed_count += 1

        # Commit all changes
        await session.commit()

    logger.info("=== Sync Complete ===")
    logger.info(f"Synced: {synced_count}")
    logger.info(f"Failed: {failed_count}")


def main_cli() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Sync voice samples from Modal volume to Senda database and S3"
    )
    parser.add_argument(
        "--modal-token-id",
        default=os.getenv("MODAL_TOKEN_ID"),
        help="Modal API token ID (defaults to MODAL_TOKEN_ID from .env)",
    )
    parser.add_argument(
        "--modal-token-secret",
        default=os.getenv("MODAL_TOKEN_SECRET"),
        help="Modal API token secret (defaults to MODAL_TOKEN_SECRET from .env)",
    )
    parser.add_argument(
        "--filter", help="Optional filter to sync only voices matching this pattern"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force synchronization and regeneration of samples for existing voices",
    )

    args = parser.parse_args()

    # Validate credentials are available and properly formatted
    try:
        validate_modal_credentials(args.modal_token_id, args.modal_token_secret)
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    try:
        asyncio.run(
            main(
                modal_token_id=args.modal_token_id,
                modal_token_secret=args.modal_token_secret,
                voice_filter=args.filter,
                force=args.force,
            )
        )
    except KeyboardInterrupt:
        logger.info("Sync interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main_cli()
