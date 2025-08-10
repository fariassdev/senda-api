from sqlalchemy.orm import Session
from src.senda.api.models import course as models
from src.senda.api.schemas import course as schemas


class CourseRepository:
    def get_course(self, db: Session, course_id: int):
        return db.query(models.Course).filter(models.Course.id == course_id).first()

    def create_course(self, db: Session, course: schemas.CourseCreate):
        # Create the Course DB model instance from the schema
        db_course = models.Course(
            title=course.title,
            description=course.description,
            total_lessons=course.total_lessons,
            tags=course.tags,
            # 'active' defaults to False in the model
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

        # Refresh the course instance to load the newly created lessons
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


course_repository = CourseRepository()
