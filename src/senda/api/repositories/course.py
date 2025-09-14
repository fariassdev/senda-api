from sqlalchemy.orm import Session
from src.senda.api.schemas.lesson import ScriptPart
from src.senda.api.schemas.course import CourseCreate, CourseUpdate
from src.senda.api.models.course import Course
from src.senda.api.models.lesson import Lesson, LessonStatus


class CourseRepository:
    def get_course(self, db: Session, course_id: int):
        return db.query(Course).filter(Course.id == course_id).first()

    def create_course(self, db: Session, course: CourseCreate):
        # Create the Course DB model instance from the schema
        db_course = Course(
            title=course.title,
            description=course.description,
            tags=course.tags,
        )
        db.add(db_course)
        db.commit()
        db.refresh(db_course)

        # Create the Lesson DB model instances
        for lesson_data in course.lessons:
            db_lesson = Lesson(**lesson_data.model_dump(), course_id=db_course.id)
            db.add(db_lesson)
        db.commit()

        db.refresh(db_course)
        return db_course

    def get_lesson(self, db: Session, course_id: int, lesson_id: int):
        return (
            db.query(Lesson)
            .filter(Lesson.course_id == course_id, Lesson.id == lesson_id)
            .first()
        )

    def update_lesson_status(
        self,
        db: Session,
        lesson: Lesson,
        status: LessonStatus,
    ):
        lesson.status = status
        db.add(lesson)
        db.commit()
        db.refresh(lesson)
        return lesson

    def update_lesson_script(
        self,
        db: Session,
        lesson: Lesson,
        script_content: list[ScriptPart],
        status: LessonStatus,
    ):
        lesson.script = [script_line.model_dump() for script_line in script_content]
        lesson.status = status
        db.add(lesson)
        db.commit()
        db.refresh(lesson)
        return lesson

    def get_ungenerated_lessons(self, db: Session, course_id: int):
        return (
            db.query(Lesson)
            .filter(
                Lesson.course_id == course_id,
                Lesson.status.in_([LessonStatus.PENDING, LessonStatus.SCRIPT_FAILED]),
            )
            .all()
        )

    def update_course(
        self, db: Session, db_course: Course, course_update: CourseUpdate
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
