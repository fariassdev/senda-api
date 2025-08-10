from typing import Any, Dict, List
from sqlalchemy.orm import Session
from src.senda.api.models import course as models
from src.senda.api.schemas import course as schemas


class CourseRepository:
    def get_course(self, db: Session, course_id: int):
        return db.query(models.Course).filter(models.Course.id == course_id).first()

    def create_course(self, db: Session, course: schemas.CourseCreate):
        if course.total_lessons != len(course.lessons):
            print(
                f"Warning: LLM 'totalLessons' ({course.total_lessons}) does not match lesson count ({len(course.lessons)})."
            )

        # Create the Course DB model instance from the schema
        db_course = models.Course(
            title=course.title,
            description=course.description,
            tags=course.tags,
        )
        db.add(db_course)
        db.commit()
        db.refresh(db_course)

        # Create the Lesson DB model instances
        for lesson_data in course.lessons:
            db_lesson = models.Lesson(
                **lesson_data.model_dump(), course_id=db_course.id
            )
            db.add(db_lesson)
        db.commit()

        db.refresh(db_course)
        return db_course

    def get_lesson(self, db: Session, course_id: int, lesson_id: int):
        return (
            db.query(models.Lesson)
            .filter(models.Lesson.course_id == course_id, models.Lesson.id == lesson_id)
            .first()
        )

    def update_lesson_status(
        self,
        db: Session,
        lesson: models.Lesson,
        status: models.LessonStatus,
        audio_url: str = None,
    ):
        lesson.status = status
        if audio_url:
            lesson.audio_url = audio_url
        db.add(lesson)
        db.commit()
        db.refresh(lesson)
        return lesson

    def update_lesson_script(
        self,
        db: Session,
        lesson: models.Lesson,
        script_content: List[Dict[str, Any]],
        status: models.LessonStatus,
    ):
        lesson.script = script_content
        lesson.status = status
        db.add(lesson)
        db.commit()
        db.refresh(lesson)
        return lesson

    def get_ungenerated_lessons(self, db: Session, course_id: int):
        return (
            db.query(models.Lesson)
            .filter(
                models.Lesson.course_id == course_id,
                models.Lesson.status.in_(
                    [models.LessonStatus.NOT_GENERATED, models.LessonStatus.FAILED]
                ),
            )
            .all()
        )

    def update_course(
        self, db: Session, db_course: models.Course, course_update: schemas.CourseUpdate
    ):
        update_data = course_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "image_placeholder_url" and value is not None:
                setattr(db_course, key, value.unicode_string())
            else:
                setattr(db_course, key, value)
        db.add(db_course)
        db.commit()
        db.refresh(db_course)
        return db_course


course_repository = CourseRepository()
