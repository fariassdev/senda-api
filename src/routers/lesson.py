from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from core.database import get_db
from repositories.course import CourseRepository
from repositories.lesson import LessonRepository
from services.lesson_script_service import LessonScriptService
from services.audio_service import AudioService
from services.s3_service import S3Service
from services.lesson_script_writer import (
    LessonScriptWriter,
    GeminiLessonScriptWriter,
)

router = APIRouter(
    prefix="/lessons",
    tags=["lessons"],
)


def get_course_repository(db: Session = Depends(get_db)) -> CourseRepository:
    return CourseRepository(db)


def get_lesson_repository(db: Session = Depends(get_db)) -> LessonRepository:
    return LessonRepository(db)


def get_lesson_script_writer() -> LessonScriptWriter:
    """Dependency provider for the LessonScriptWriter service."""
    return GeminiLessonScriptWriter()


def get_lesson_service(
    script_writer: LessonScriptWriter = Depends(get_lesson_script_writer),
    course_repository: CourseRepository = Depends(get_course_repository),
    lesson_repository: LessonRepository = Depends(get_lesson_repository),
) -> LessonScriptService:
    """Dependency provider for the LessonScriptService."""
    return LessonScriptService(script_writer, course_repository, lesson_repository)


def get_s3_service() -> S3Service:
    return S3Service()


def get_audio_service(s3_service: S3Service = Depends(get_s3_service)) -> AudioService:
    return AudioService(s3_service)


# In a real application, this would be a proper task queue (e.g., Celery)
_generating_lessons = set()


async def _generate_audio_task(
    lesson_id: UUID,
    lesson_repo: LessonRepository,
    audio_service: AudioService,
):
    """Background task for generating lesson audio."""
    lesson = lesson_repo.get_lesson(lesson_id)
    if not lesson:
        print(f"Lesson with id {lesson_id} not found.")
        return

    try:
        audio_service.generate_lesson_audio(lesson, lesson_repo)
    except Exception as e:
        print(f"Failed to generate audio for lesson {lesson_id}: {e}")


async def _generate_lesson_task(
    lesson_id: UUID,
    lesson_service: LessonScriptService,
):
    """Background task for generating lesson script."""
    try:
        lesson_service.generate_and_save_lesson_script(lesson_id)
    except Exception as e:
        print(f"Error generating script for lesson {lesson_id}: {e}")


@router.post("/{lesson_id}/generate-audio", status_code=202)
async def generate_lesson_audio(
    lesson_id: UUID,
    background_tasks: BackgroundTasks,
    lesson_repo: LessonRepository = Depends(get_lesson_repository),
    audio_service: AudioService = Depends(get_audio_service),
):
    background_tasks.add_task(
        _generate_audio_task, lesson_id, lesson_repo, audio_service
    )
    return {"message": "Audio generation for lesson started in background"}


@router.post("/{lesson_id}/generate-script", status_code=202)
async def generate_lesson_script(
    lesson_id: UUID,
    background_tasks: BackgroundTasks,
    lesson_service: LessonScriptService = Depends(get_lesson_service),
):
    if (lesson_id) in _generating_lessons:
        raise HTTPException(
            status_code=409, detail="Lesson script generation already in progress"
        )

    _generating_lessons.add((lesson_id))
    background_tasks.add_task(_generate_lesson_task, lesson_id, lesson_service)
    return {"message": "Script generation for lesson started in background"}
