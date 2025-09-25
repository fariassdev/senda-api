from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime, timezone

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
