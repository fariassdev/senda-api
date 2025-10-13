from uuid import UUID
from models.lesson import Lesson, LessonStatus
from repositories.lesson import LessonRepository
from repositories.course import CourseRepository
from services.lesson_script_writer.lesson_script_writer import (
    LessonScriptWriter,
)
from services.event_publisher import EventPublisher


class LessonScriptService:
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
        """Generate and save a lesson script, always emitting per-lesson events."""
        lesson = self.lesson_repository.get_lesson(lesson_id)
        if not lesson:
            raise ValueError(f"Lesson with ID {lesson_id} not found")

        EventPublisher.publish_lesson_script_started(lesson_id)

        self.lesson_repository.update_lesson_status(
            lesson, LessonStatus.SCRIPT_GENERATING
        )

        course = self.course_repository.get_course(lesson.course_id)
        if not course:
            raise ValueError(f"Course with ID {lesson.course_id} not found")

        total_lessons = len(course.lessons)

        course_context = {
            "name": course.title,
            "description": course.description,
            "totalLessons": total_lessons,
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

            EventPublisher.publish_lesson_script_completed(
                lesson_id, updated_lesson.script
            )
            return updated_lesson
        except Exception as e:
            print(f"Error generating script for lesson {lesson.id}: {e}")
            self.lesson_repository.update_lesson_status(
                lesson, LessonStatus.SCRIPT_FAILED
            )

            EventPublisher.publish_lesson_script_failed(lesson_id, str(e))
            raise

    def generate_and_save_all_lesson_scripts(self, course_id: UUID):
        """Generate scripts for all ungenerated lessons in a course, emitting only per-lesson events."""
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
                    updated_lesson = self.generate_and_save_lesson_script(lesson.id)
                    generated_lessons.append(updated_lesson)
                except Exception as e:
                    print(f"Error generating script for lesson {lesson.id}: {e}")
        return generated_lessons
