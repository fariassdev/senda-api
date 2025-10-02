from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional

from src.senda.api.schemas.lesson import ScriptPart
from src.senda.api.models.lesson import LessonStatus, Lesson


class LessonRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_lesson(self, lesson_id: UUID) -> Lesson | None:
        return self.db.query(Lesson).filter(Lesson.id == lesson_id).first()

    def update_lesson(self, lesson: Lesson) -> Lesson:
        self.db.add(lesson)
        self.db.commit()
        self.db.refresh(lesson)
        return lesson

    def update_lesson_status(
        self,
        lesson: Lesson,
        status: LessonStatus,
    ):
        lesson.status = status
        self.db.add(lesson)
        self.db.commit()
        self.db.refresh(lesson)
        return lesson

    def update_lesson_script(
        self,
        lesson: Lesson,
        script_content: list[ScriptPart],
        status: LessonStatus,
    ):
        lesson.script = [script_line.model_dump() for script_line in script_content]
        lesson.status = status

        if status == LessonStatus.SCRIPT_COMPLETED:
            lesson.script_generated_at = datetime.now(timezone.utc)

        self.db.add(lesson)
        self.db.commit()
        self.db.refresh(lesson)
        return lesson

    def update_lesson_metadata(
        self,
        lesson: Lesson,
        title: Optional[str] = None,
        core_practice: Optional[str] = None,
        key_point: Optional[str] = None,
        tone: Optional[str] = None,
        duration_minutes: Optional[int] = None,
    ) -> Lesson:
        """Update lesson metadata fields and set needs_regeneration if any content changed."""
        original_content = {
            "title": lesson.title,
            "core_practice": lesson.core_practice,
            "key_point": lesson.key_point,
            "tone": lesson.tone,
            "duration_minutes": lesson.duration_minutes,
        }

        if title is not None:
            lesson.title = title
        if core_practice is not None:
            lesson.core_practice = core_practice
        if key_point is not None:
            lesson.key_point = key_point
        if tone is not None:
            lesson.tone = tone
        if duration_minutes is not None:
            lesson.duration_minutes = duration_minutes

        # Check if any content fields changed
        content_changed = any(
            getattr(lesson, field) != original_content[field]
            for field in [
                "title",
                "core_practice",
                "key_point",
                "tone",
                "duration_minutes",
            ]
        )

        if content_changed:
            lesson.needs_regeneration = True

        self.db.add(lesson)
        self.db.commit()
        self.db.refresh(lesson)
        return lesson
