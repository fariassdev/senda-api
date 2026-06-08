import enum
from functools import total_ordering


@total_ordering
class UserRole(str, enum.Enum):
    """User role enumeration with ordering support (USER < ADMIN)"""

    USER = "USER"
    ADMIN = "ADMIN"

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, UserRole):
            return NotImplemented
        role_order = {UserRole.USER: 1, UserRole.ADMIN: 2}
        return role_order[self] < role_order[other]


class DifficultyLevel(str, enum.Enum):
    """Course difficulty level enumeration"""

    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class TtsProvider(str, enum.Enum):
    """Supported text-to-speech backends."""

    CHATTERBOX = "chatterbox"
    KOKORO = "kokoro"


class ScriptPartType(str, enum.Enum):
    """Script part type enumeration for lesson scripts"""

    SPEAK = "speak"
    PAUSE = "pause"


class LessonStatus(str, enum.Enum):
    """Lesson status enumeration for tracking lesson generation workflow"""

    PENDING = "PENDING"
    SCRIPT_GENERATING = "SCRIPT_GENERATING"
    SCRIPT_COMPLETED = "SCRIPT_COMPLETED"
    SCRIPT_FAILED = "SCRIPT_FAILED"
    AUDIO_GENERATING = "AUDIO_GENERATING"
    AUDIO_COMPLETED = "AUDIO_COMPLETED"
    AUDIO_FAILED = "AUDIO_FAILED"
    READY_TO_PUBLISH = "READY_TO_PUBLISH"


class AudioGenerationJobStatus(str, enum.Enum):
    """Operational status for an HLS audio generation job."""

    PENDING = "PENDING"
    GENERATING = "GENERATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
