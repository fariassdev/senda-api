from sqlalchemy.orm import Session
from src.senda.api.models.lesson import Lesson, LessonStatus
from src.senda.api.repositories.course import CourseRepository
from src.senda.api.services.lesson_script_writer.lesson_script_writer import (
    LessonScriptWriter,
)


class LessonService:
    def __init__(
        self, script_writer: LessonScriptWriter, course_repository: CourseRepository
    ):
        self.script_writer = script_writer
        self.course_repository = course_repository

    def generate_and_save_lesson_script(
        self, db: Session, course_id: int, lesson_id: int
    ) -> Lesson:
        lesson = self.course_repository.get_lesson(db, course_id, lesson_id)
        if not lesson:
            raise ValueError(
                f"Lesson with ID {lesson_id} not found in course {course_id}"
            )

        self.course_repository.update_lesson_status(
            db, lesson, LessonStatus.SCRIPT_GENERATING
        )

        course = self.course_repository.get_course(db, course_id)
        if not course:
            raise ValueError(f"Course with ID {course_id} not found")

        course_context = {
            "name": course.title,
            "description": course.description,
            "totalLessons": course.total_lessons,
        }
        lesson_details = {
            "lessonNumber": lesson.lesson_number,
            "title": lesson.title,
            "corePractice": lesson.core_practice,
            "durationMinutes": lesson.duration_minutes,
            "keyPoint": lesson.key_point,
            "tone": lesson.tone,
        }

        try:
            script_content = self.script_writer.generate_script(
                course_context, lesson_details
            )

            updated_lesson = self.course_repository.update_lesson_script(
                db, lesson, script_content, LessonStatus.SCRIPT_COMPLETED
            )
            return updated_lesson
        except Exception as e:
            print(f"Error generating script for lesson {lesson.id}: {e}")
            self.course_repository.update_lesson_status(
                db, lesson, LessonStatus.SCRIPT_FAILED
            )
            raise

    def generate_and_save_all_lesson_scripts(self, db: Session, course_id: int):
        lessons = self.course_repository.get_ungenerated_lessons(db, course_id)
        if not lessons:
            return []

        generated_lessons = []
        for lesson in lessons:
            if lesson.status in [
                LessonStatus.PENDING,
                LessonStatus.SCRIPT_FAILED,
            ]:
                try:
                    updated_lesson = self.generate_and_save_lesson_script(
                        db, course_id, lesson.id
                    )
                    generated_lessons.append(updated_lesson)
                except Exception as e:
                    print(f"Error generating script for lesson {lesson.id}: {e}")
        return generated_lessons
