import enum


class UserRole(str, enum.Enum):
    """User role enumeration"""

    USER = "USER"
    ADMIN = "ADMIN"


class DifficultyLevel(str, enum.Enum):
    """Course difficulty level enumeration"""

    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


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
