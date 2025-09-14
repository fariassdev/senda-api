from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from src.senda.api.core.database import get_db
from src.senda.api.repositories.lesson import LessonRepository
from src.senda.api.services.audio_service import AudioService
from src.senda.api.services.s3_service import S3Service
from src.senda.api.models.lesson import LessonStatus

router = APIRouter(
    prefix="/lessons",
    tags=["lessons"],
)


def get_lesson_repository(db: Session = Depends(get_db)) -> LessonRepository:
    return LessonRepository(db)


def get_s3_service() -> S3Service:
    return S3Service()


def get_audio_service(s3_service: S3Service = Depends(get_s3_service)) -> AudioService:
    return AudioService(s3_service)


async def _generate_audio_task(
    lesson_id: int,
    lesson_repo: LessonRepository,
    audio_service: AudioService,
):
    lesson = lesson_repo.get_lesson(lesson_id)
    if not lesson:
        print(f"Lesson with id {lesson_id} not found.")
        return

    lesson.status = LessonStatus.AUDIO_GENERATING
    lesson_repo.update_lesson(lesson)

    try:
        audio_url = audio_service.generate_and_upload_lesson_audio(lesson)
        if audio_url:
            lesson.audio_url = audio_url
            lesson.status = LessonStatus.AUDIO_COMPLETED
            lesson_repo.update_lesson(lesson)
            print(f"Audio generated successfully for lesson {lesson_id}")
        else:
            lesson.status = LessonStatus.AUDIO_FAILED
            lesson_repo.update_lesson(lesson)
            print(
                f"Audio generation failed for lesson {lesson_id}: No audio URL returned."
            )
    except Exception as e:
        lesson.status = LessonStatus.AUDIO_FAILED
        lesson_repo.update_lesson(lesson)
        print(f"Failed to generate audio for lesson {lesson_id}: {e}")


@router.post("/{lesson_id}/generate-audio", status_code=202)
async def generate_lesson_audio(
    lesson_id: int,
    background_tasks: BackgroundTasks,
    lesson_repo: LessonRepository = Depends(get_lesson_repository),
    audio_service: AudioService = Depends(get_audio_service),
):
    background_tasks.add_task(
        _generate_audio_task, lesson_id, lesson_repo, audio_service
    )
    return {"message": "Audio generation for lesson started in background"}
