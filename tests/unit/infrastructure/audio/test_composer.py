"""Unit tests for HLS audio composer helpers."""

from senda.infrastructure.audio.composer import (
    ensure_endlist,
    parse_duration_ms_from_playlist,
    playlist_url_for,
    rewrite_playlist_with_cdn_urls,
    strip_endlist,
)


class TestPlaylistHelpers:
    def test_rewrite_playlist_with_cdn_urls(self) -> None:
        content = (
            "#EXTM3U\n"
            "#EXT-X-VERSION:3\n"
            "#EXTINF:6.000,\n"
            "segment_000.ts\n"
            "#EXTINF:6.000,\n"
            "segment_001.ts\n"
        )

        rewritten = rewrite_playlist_with_cdn_urls(
            content,
            cdn_base_url="https://cdn.senda.com",
            s3_base_path="meditations/42/job-id",
        )

        assert "https://cdn.senda.com/meditations/42/job-id/segment_000.ts" in rewritten
        assert "https://cdn.senda.com/meditations/42/job-id/segment_001.ts" in rewritten

    def test_parse_duration_ms_from_playlist(self) -> None:
        content = "#EXTINF:6.000,\n#EXTINF:4.500,\n"
        assert parse_duration_ms_from_playlist(content) == 10500

    def test_strip_and_ensure_endlist(self) -> None:
        live = "#EXTM3U\n#EXT-X-ENDLIST\n"
        stripped = strip_endlist(live)
        assert "#EXT-X-ENDLIST" not in stripped

        final = ensure_endlist(stripped)
        assert final.endswith("#EXT-X-ENDLIST\n")

    def test_playlist_url_for(self) -> None:
        url = playlist_url_for("https://cdn.senda.com", "meditations/42/job-id/")
        assert url == "https://cdn.senda.com/meditations/42/job-id/playlist.m3u8"
