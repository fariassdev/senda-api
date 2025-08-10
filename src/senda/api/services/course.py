from sqlalchemy.orm import Session
from src.senda.api.models import course as models
from src.senda.api.schemas import course as schemas


class CourseService:
    def get_course(self, db: Session, course_id: str):
        return db.query(models.Course).filter(models.Course.id == course_id).first()

    def create_course(self, db: Session, course: schemas.CourseCreate):
        db_course = models.Course(
            id=course.id,
            title=course.title,
            description=course.description,
            author=course.author,
            image_placeholder_url=course.image_placeholder_url.unicode_string(),
        )
        db.add(db_course)
        db.commit()
        db.refresh(db_course)

        for lesson_data in course.lessons:
            db_lesson = models.Lesson(
                **lesson_data.model_dump(), course_id=db_course.id
            )
            db.add(db_lesson)
        db.commit()
        db.refresh(db_course)
        return db_course

    def get_lesson(self, db: Session, course_id: str, lesson_id: int):
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
        script_url: str = None,
        audio_url: str = None,
    ):
        lesson.status = status
        if script_url:
            lesson.script_url = script_url
        if audio_url:
            lesson.audio_url = audio_url
        db.add(lesson)
        db.commit()
        db.refresh(lesson)
        return lesson

    def get_ungenerated_lessons(self, db: Session, course_id: str):
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


course_service = CourseService()
