from sqlalchemy.orm import Session

from src.senda.api.models.course import Lesson


class LessonRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_lesson(self, lesson_id: int) -> Lesson | None:
        return self.db.query(Lesson).filter(Lesson.id == lesson_id).first()

    def update_lesson(self, lesson: Lesson) -> Lesson:
        self.db.add(lesson)
        self.db.commit()
        self.db.refresh(lesson)
        return lesson
