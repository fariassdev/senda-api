"""Estimate meditation audio duration from script content."""

from senda.core.enums import ScriptPartType
from senda.domain.dtos.script_generation import ScriptPartDTO

# Matches senda-cms ScriptPreview MEDITATION_WORDS_PER_MINUTE
MEDITATION_WORDS_PER_MINUTE = 113


def estimate_script_duration_ms(
    script_parts: list[ScriptPartDTO], *, target_duration_minutes: int | None = None
) -> int:
    """Estimate total audio length from speak/pause script parts."""
    word_count = 0
    pause_seconds = 0.0

    for part in script_parts:
        if part.type == ScriptPartType.SPEAK and part.content:
            word_count += len(part.content.strip().split())
        elif part.type == ScriptPartType.PAUSE and part.duration:
            pause_seconds += max(part.duration, 0.0)

    reading_seconds = round((word_count / MEDITATION_WORDS_PER_MINUTE) * 60)
    total_seconds = reading_seconds + int(pause_seconds)

    if total_seconds > 0:
        return total_seconds * 1000

    if target_duration_minutes and target_duration_minutes > 0:
        return target_duration_minutes * 60 * 1000

    return 0
