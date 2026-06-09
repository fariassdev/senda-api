"""HLS audio composition via ffmpeg and incremental S3 uploads."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import shutil
import tempfile
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from senda.core.enums import ScriptPartType
from senda.core.exceptions import AudioGenerationException
from senda.domain.dtos.script_generation import ScriptPartDTO
from senda.domain.services.audio_generation import IStorageProvider
from senda.infrastructure.utils.audio_processor import (
    CHANNELS,
    SAMPLE_RATE,
    SAMPLE_WIDTH,
    AudioProcessor,
)

logger = logging.getLogger(__name__)

PLAYLIST_FILENAME = "playlist.m3u8"
CONTENT_TYPE_MANIFEST = "application/vnd.apple.mpegurl"
CONTENT_TYPE_SEGMENT = "video/mp2t"
CACHE_LIVE_MANIFEST = "no-cache, no-store"
CACHE_IMMUTABLE = "public, max-age=31536000"
WATCH_POLL_INTERVAL_SECONDS = 0.5
EXTINF_PATTERN = re.compile(r"#EXTINF:([0-9.]+),")
ENDLIST_TAG = "#EXT-X-ENDLIST"


@dataclass(frozen=True)
class HlsCompositionResult:
    """Result of a completed HLS composition."""

    duration_ms: int
    playlist_url: str


def normalize_base_path(s3_base_path: str) -> str:
    """Ensure S3 base path ends with a slash."""
    return s3_base_path if s3_base_path.endswith("/") else f"{s3_base_path}/"


def playlist_url_for(cdn_base_url: str, s3_base_path: str) -> str:
    base_path = normalize_base_path(s3_base_path)
    return f"{cdn_base_url.rstrip('/')}/{base_path}{PLAYLIST_FILENAME}"


def rewrite_playlist_with_cdn_urls(
    playlist_content: str,
    cdn_base_url: str,
    s3_base_path: str,
    uploaded_segments: set[str] | None = None,
) -> str:
    """Replace relative segment paths with absolute CDN URLs, filtering out un-uploaded segments."""
    base_path = normalize_base_path(s3_base_path)
    cdn_prefix = f"{cdn_base_url.rstrip('/')}/{base_path}"
    rewritten_lines: list[str] = []
    buffered_extinf: str | None = None

    for line in playlist_content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#EXTINF:"):
            buffered_extinf = line
            continue

        if stripped.endswith(".ts") and not stripped.startswith("http"):
            segment_name = stripped
            if uploaded_segments is None or segment_name in uploaded_segments:
                if buffered_extinf is not None:
                    rewritten_lines.append(buffered_extinf)
                    buffered_extinf = None
                rewritten_lines.append(f"{cdn_prefix}{segment_name}")
            else:
                buffered_extinf = None
        else:
            if buffered_extinf is not None:
                rewritten_lines.append(buffered_extinf)
                buffered_extinf = None
            rewritten_lines.append(line)

    return "\n".join(rewritten_lines) + "\n"


def strip_endlist(playlist_content: str) -> str:
    lines = [
        line for line in playlist_content.splitlines() if line.strip() != ENDLIST_TAG
    ]
    return "\n".join(lines) + "\n"


def ensure_endlist(playlist_content: str) -> str:
    content = strip_endlist(playlist_content)
    if not content.endswith("\n"):
        content += "\n"
    return content + f"{ENDLIST_TAG}\n"


def parse_duration_ms_from_playlist(playlist_content: str) -> int:
    """Sum #EXTINF durations from a playlist and return total milliseconds."""
    total_seconds = sum(
        float(match) for match in EXTINF_PATTERN.findall(playlist_content)
    )
    return int(total_seconds * 1000)


class AudioComposer:
    """Compose lesson audio into HLS segments and upload incrementally to S3."""

    def __init__(
        self,
        storage_provider: IStorageProvider,
        segment_seconds: int = 6,
        cdn_base_url: str | None = None,
        sample_rate: int = SAMPLE_RATE,
        sample_width: int = SAMPLE_WIDTH,
        channels: int = CHANNELS,
        silence_fallback_seconds: float = 2.0,
        audio_processor: AudioProcessor | None = None,
    ) -> None:
        self._storage = storage_provider
        self._segment_seconds = segment_seconds
        self._cdn_base_url = cdn_base_url
        self._sample_rate = sample_rate
        self._sample_width = sample_width
        self._channels = channels
        self._silence_fallback_seconds = silence_fallback_seconds
        self._audio_processor = audio_processor or AudioProcessor(
            sample_rate=sample_rate, channels=channels, sample_width=sample_width
        )

    def _resolve_cdn_base_url(self, cdn_base_url: str | None) -> str:
        if cdn_base_url:
            return cdn_base_url.rstrip("/")
        if self._cdn_base_url:
            return self._cdn_base_url.rstrip("/")
        return self._storage.public_url_for_key("").rstrip("/")

    def _silence_pcm(self, duration_seconds: float) -> bytes:
        if duration_seconds <= 0:
            return b""
        sample_count = int(self._sample_rate * duration_seconds)
        return b"\x00\x00" * sample_count

    async def _pcm_for_script_part(
        self,
        part: ScriptPartDTO,
        idx: int,
        speech_data: Callable[[int], Awaitable[bytes | None]],
    ) -> bytes:
        if part.type == ScriptPartType.SPEAK:
            pcm = await speech_data(idx)
            if not pcm:
                logger.warning(
                    "Missing TTS audio for script part %s — using %.1fs silence fallback",
                    idx + 1,
                    self._silence_fallback_seconds,
                )
                return self._silence_pcm(self._silence_fallback_seconds)
            return pcm

        if part.type == ScriptPartType.PAUSE:
            duration = part.duration or 0.0
            if duration <= 0:
                logger.warning(
                    "Script part %s has invalid pause duration, skipping", idx + 1
                )
                return b""
            return self._audio_processor.create_silence(duration).raw_data

        logger.warning(
            "Unknown script part type %s at index %s, skipping", part.type, idx
        )
        return b""

    def _ffmpeg_args(self, tmp_dir: Path) -> list[str]:
        segment_pattern = str(tmp_dir / "segment_%03d.ts")
        playlist_path = str(tmp_dir / PLAYLIST_FILENAME)
        return [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "s16le",
            "-ar",
            str(self._sample_rate),
            "-ac",
            str(self._channels),
            "-i",
            "pipe:0",
            "-codec:a",
            "aac",
            "-b:a",
            "128k",
            "-f",
            "hls",
            "-hls_time",
            str(self._segment_seconds),
            "-hls_list_size",
            "0",
            "-hls_flags",
            "append_list+omit_endlist+independent_segments",
            "-hls_segment_type",
            "mpegts",
            "-hls_segment_filename",
            segment_pattern,
            playlist_path,
        ]

    async def compose_hls(
        self,
        *,
        job_id: UUID,
        script_parts: list[ScriptPartDTO],
        speech_data: Callable[[int], Awaitable[bytes | None]],
        s3_base_path: str,
        cdn_base_url: str | None = None,
        on_segment_ready: Callable[[int], Awaitable[None]] | None = None,
    ) -> HlsCompositionResult:
        """Feed PCM to ffmpeg, upload HLS segments incrementally, return artifact metadata."""
        if not script_parts:
            raise AudioGenerationException(
                message="Cannot compose HLS from empty script"
            )

        resolved_cdn = self._resolve_cdn_base_url(cdn_base_url)
        base_path = normalize_base_path(s3_base_path)
        tmp_dir = Path(tempfile.gettempdir()) / str(job_id)
        tmp_dir.mkdir(parents=True, exist_ok=True)

        proc: asyncio.subprocess.Process | None = None
        stderr_task: asyncio.Task | None = None

        try:
            proc = await asyncio.create_subprocess_exec(
                *self._ffmpeg_args(tmp_dir),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            if proc.stdin is None or proc.stderr is None:
                raise AudioGenerationException(message="Failed to start ffmpeg process")

            stderr_task = asyncio.create_task(self._drain_stderr(proc))

            await asyncio.gather(
                self._write_script_pcm(proc, script_parts, speech_data),
                self._watch_and_upload(
                    tmp_dir=tmp_dir,
                    base_path=base_path,
                    cdn_base_url=resolved_cdn,
                    proc=proc,
                    on_segment_ready=on_segment_ready,
                ),
            )

            returncode = await proc.wait()
            if returncode != 0:
                raise AudioGenerationException(
                    message=f"ffmpeg exited with status {returncode}"
                )

            playlist_path = tmp_dir / PLAYLIST_FILENAME
            if not playlist_path.exists():
                raise AudioGenerationException(
                    message="ffmpeg did not produce playlist.m3u8"
                )

            final_playlist = ensure_endlist(playlist_path.read_text(encoding="utf-8"))
            final_playlist = rewrite_playlist_with_cdn_urls(
                final_playlist, resolved_cdn, base_path
            )
            await self._storage.upload_file(
                file_data=final_playlist.encode("utf-8"),
                key=f"{base_path}{PLAYLIST_FILENAME}",
                content_type=CONTENT_TYPE_MANIFEST,
                cache_control=CACHE_IMMUTABLE,
            )

            duration_ms = parse_duration_ms_from_playlist(final_playlist)

            return HlsCompositionResult(
                duration_ms=duration_ms,
                playlist_url=playlist_url_for(resolved_cdn, base_path),
            )
        except Exception:
            if proc and proc.returncode is None:
                proc.kill()
                await proc.wait()
            raise
        finally:
            if stderr_task:
                stderr_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await stderr_task
            shutil.rmtree(tmp_dir, ignore_errors=True)

    async def _drain_stderr(self, proc: asyncio.subprocess.Process) -> None:
        if proc.stderr is None:
            return
        while True:
            line = await proc.stderr.readline()
            if not line:
                break
            logger.debug("ffmpeg: %s", line.decode("utf-8", errors="replace").rstrip())

    async def _write_script_pcm(
        self,
        proc: asyncio.subprocess.Process,
        script_parts: list[ScriptPartDTO],
        speech_data: Callable[[int], Awaitable[bytes | None]],
    ) -> None:
        if proc.stdin is None:
            raise AudioGenerationException(message="ffmpeg stdin is not available")

        try:
            for idx, part in enumerate(script_parts):
                pcm = await self._pcm_for_script_part(part, idx, speech_data)
                if not pcm:
                    continue
                proc.stdin.write(pcm)
                await proc.stdin.drain()
        finally:
            proc.stdin.close()
            await proc.stdin.wait_closed()

    async def _watch_and_upload(
        self,
        *,
        tmp_dir: Path,
        base_path: str,
        cdn_base_url: str,
        proc: asyncio.subprocess.Process,
        on_segment_ready: Callable[[int], Awaitable[None]] | None,
    ) -> None:
        uploaded_segments: set[str] = set()
        segments_available = 0
        playlist_key = f"{base_path}{PLAYLIST_FILENAME}"

        while True:
            ts_files = sorted(tmp_dir.glob("segment_*.ts"))
            ffmpeg_done = proc.returncode is not None

            pending_uploads: list[Path] = []
            for index, ts_file in enumerate(ts_files):
                if ts_file.name in uploaded_segments:
                    continue

                next_segment_exists = index + 1 < len(ts_files)
                if not next_segment_exists and not ffmpeg_done:
                    continue

                pending_uploads.append(ts_file)

            if pending_uploads:

                async def upload_one_segment(ts_file: Path) -> str:
                    segment_bytes = ts_file.read_bytes()
                    await self._storage.upload_file(
                        file_data=segment_bytes,
                        key=f"{base_path}{ts_file.name}",
                        content_type=CONTENT_TYPE_SEGMENT,
                        cache_control=CACHE_IMMUTABLE,
                    )
                    return ts_file.name

                uploaded_names = await asyncio.gather(
                    *(upload_one_segment(f) for f in pending_uploads)
                )

                for name in uploaded_names:
                    uploaded_segments.add(name)
                segments_available += len(uploaded_names)

                if on_segment_ready is not None:
                    await on_segment_ready(segments_available)

                playlist_path = tmp_dir / PLAYLIST_FILENAME
                if playlist_path.exists():
                    live_playlist = strip_endlist(
                        playlist_path.read_text(encoding="utf-8")
                    )
                    live_playlist = rewrite_playlist_with_cdn_urls(
                        live_playlist, cdn_base_url, base_path, uploaded_segments
                    )
                    if ".ts" in live_playlist:
                        await self._storage.upload_file(
                            file_data=live_playlist.encode("utf-8"),
                            key=playlist_key,
                            content_type=CONTENT_TYPE_MANIFEST,
                            cache_control=CACHE_LIVE_MANIFEST,
                        )

            if ffmpeg_done and len(uploaded_segments) == len(ts_files):
                break

            await asyncio.sleep(WATCH_POLL_INTERVAL_SECONDS)
