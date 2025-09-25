from uuid import UUID
from datetime import datetime
from src.senda.api.models.lesson import Lesson, LessonStatus
from src.senda.api.repositories.lesson import LessonRepository
from src.senda.api.repositories.course import CourseRepository
from src.senda.api.services.lesson_script_writer.lesson_script_writer import (
    LessonScriptWriter,
)


class LessonService:
    def __init__(
        self,
        script_writer: LessonScriptWriter,
        course_repository: CourseRepository,
        lesson_repository: LessonRepository,
    ):
        self.script_writer = script_writer
        self.course_repository = course_repository
        self.lesson_repository = lesson_repository

    def generate_and_save_lesson_script(self, lesson_id: UUID) -> Lesson:
        lesson = self.lesson_repository.get_lesson(lesson_id)
        if not lesson:
            raise ValueError(f"Lesson with ID {lesson_id} not found")

        self.lesson_repository.update_lesson_status(
            lesson, LessonStatus.SCRIPT_GENERATING
        )

        course = self.course_repository.get_course(lesson.course_id)
        if not course:
            raise ValueError(f"Course with ID {lesson.course_id} not found")

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

            updated_lesson = self.lesson_repository.update_lesson_script(
                lesson, script_content, LessonStatus.SCRIPT_COMPLETED
            )
            # Set script generation timestamp
            updated_lesson.script_generated_at = datetime.utcnow()
            self.lesson_repository.update_lesson(updated_lesson)
            return updated_lesson
        except Exception as e:
            print(f"Error generating script for lesson {lesson.id}: {e}")
            self.lesson_repository.update_lesson_status(
                lesson, LessonStatus.SCRIPT_FAILED
            )
            raise

    def generate_and_save_all_lesson_scripts(self, course_id: UUID):
        lessons = self.lesson_repository.get_ungenerated_lessons(course_id)
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
                        course_id, lesson.id
                    )
                    generated_lessons.append(updated_lesson)
                except Exception as e:
                    print(f"Error generating script for lesson {lesson.id}: {e}")
        return generated_lessons
