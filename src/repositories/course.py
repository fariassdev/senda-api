from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from uuid import UUID
from schemas.course import CourseCreate, CourseUpdate
from models.course import Course
from models.lesson import Lesson, LessonStatus


class CourseRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_course(self, course_id: UUID):
        query = (
            select(Course)
            .options(joinedload(Course.lessons))
            .filter(Course.id == course_id)
        )
        return self.db.scalar(query)

    def get_courses(self, skip: int = 0, limit: int = 10):
        return self.db.query(Course).offset(skip).limit(limit).all()

    def create_course(self, course: CourseCreate):
        # Create the Course DB model instance from the schema
        db_course = Course(
            title=course.title,
            description=course.description,
            tags=course.tags,
            difficulty_level=course.difficulty_level,
        )
        self.db.add(db_course)
        self.db.commit()
        self.db.refresh(db_course)

        # Create the Lesson DB model instances
        for lesson_data in course.lessons:
            db_lesson = Lesson(**lesson_data.model_dump(), course_id=db_course.id)
            self.db.add(db_lesson)
        self.db.commit()

        self.db.refresh(db_course)
        return db_course

    def update_course(self, db_course: Course, course_update: CourseUpdate):
        update_data = course_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "image_placeholder_url" and value is not None:
                setattr(db_course, key, value.unicode_string())
            else:
                setattr(db_course, key, value)
        self.db.add(db_course)
        self.db.commit()
        self.db.refresh(db_course)
        return db_course

    def is_course_ready_to_publish(self, course_id: UUID) -> bool:
        """Check if all lessons in a course are marked as READY_TO_PUBLISH."""
        lessons_not_ready = (
            self.db.query(Lesson)
            .filter(
                Lesson.course_id == course_id,
                Lesson.status != LessonStatus.READY_TO_PUBLISH,
            )
            .first()
        )
        return lessons_not_ready is None

    def get_lessons_by_course_id(self, course_id: UUID):
        return self.db.query(Lesson).filter(Lesson.course_id == course_id).all()
