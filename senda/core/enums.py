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


class JobType(str, enum.Enum):
    """Generation job type enumeration"""

    COURSE_STRUCTURE = "course_structure"
    SCRIPT = "script"
    AUDIO = "audio"


class JobStatus(str, enum.Enum):
    """Generation job status enumeration"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
